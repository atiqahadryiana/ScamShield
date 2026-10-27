const base = (import.meta as ImportMeta & {env:Record<string,string>}).env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(message:string, public status:number) {super(message)}
}

export async function api<T>(path:string, options:RequestInit = {}):Promise<T> {
  const form = options.body instanceof FormData;
  let response:Response;
  try {
    response = await fetch(`${base}/api/v1${path}`, {...options, credentials:'include', headers:{...(!form && options.body ? {'Content-Type':'application/json'} : {}), 'X-ScamShield-Client':'web', ...options.headers}, signal:options.signal || AbortSignal.timeout(30000)});
  } catch {
    throw new ApiError('Cannot reach ScamShield. Check your connection and that the backend is running.', 0);
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.error?.message || 'Unable to complete this request.', response.status);
  return data as T;
}

export const post = <T>(path:string, data:unknown) => api<T>(path, {method:'POST',body:JSON.stringify(data)});
