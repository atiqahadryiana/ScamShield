import {Link} from 'react-router-dom';
import {LockKeyhole} from 'lucide-react';
import {useApp} from '../hooks/useApp';
export function AssessmentResultPlaceholder(){const {t}=useApp();return <div className="panel dashboard-empty"><LockKeyhole size={36}/><h1>{t('Your account, your records.','Akaun anda, rekod anda.')}</h1><p>{t('Sign in to access this private space.','Log masuk untuk mengakses ruang peribadi ini.')}</p><Link to="/login" className="button primary">{t('Sign in','Log masuk')}</Link></div>}
