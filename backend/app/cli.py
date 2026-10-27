import argparse
import getpass
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import password_hasher
from app.models.entities import User
from app.services.seed import seed
from app.services.storage import cleanup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['seed', 'create-admin', 'cleanup'])
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == 'seed':
            seed(db)
            print('Reference definitions and learning content initialized. No synthetic activity added.')
        elif args.command == 'cleanup':
            print(cleanup(db))
        else:
            email = input('Administrator email: ').strip().casefold()
            if '@' not in email or '.' not in email.rsplit('@', 1)[1]:
                raise SystemExit('Enter a valid email.')
            password = getpass.getpass('New password (at least 12 characters): ')
            if len(password) < 12 or password != getpass.getpass('Confirm password: '):
                raise SystemExit('Passwords must match and contain at least 12 characters.')
            if db.scalar(select(User).where(User.email == email)):
                raise SystemExit('An account already exists. Use a new administrator email; this command does not silently elevate users.')
            db.add(User(email=email, password_hash=password_hasher.hash(password), role='admin'))
            db.commit()
            print('Administrator created. No default credentials are supplied.')


if __name__ == '__main__':
    main()
