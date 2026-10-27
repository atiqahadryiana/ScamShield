import {useCallback, useEffect, useState} from 'react';
import {api} from '../services/api';
export function useData<T>(path:string) {
  const [data,setData]=useState<T|null>(null);
  const [error,setError]=useState('');
  const [loading,setLoading]=useState(true);
  const reload=useCallback(()=>{setLoading(true);setError('');return api<T>(path).then(setData).catch(e=>setError(e.message)).finally(()=>setLoading(false))},[path]);
  useEffect(()=>{void reload()},[reload]);
  return {data,error,loading,reload};
}
