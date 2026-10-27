import {createContext, useCallback, useContext, useEffect, useState, type ReactNode} from 'react';
import {api, post} from '../services/api';
import type {Health, User} from '../types';

interface AppState {lang:'en'|'ms';t:(en:string,ms:string)=>string;setLang:(l:'en'|'ms')=>void;dark:boolean;toggleDark:()=>void;user:User|null;setUser:(u:User|null)=>void;health:Health|null;toast:(s:string)=>void;logout:()=>Promise<void>}
const Context = createContext<AppState | null>(null);
export function AppProvider({children}:{children:ReactNode}) {
  const [lang,setLangState] = useState<'en'|'ms'>(()=>localStorage.getItem('scamshield-lang')==='ms'?'ms':'en');
  const [dark,setDark] = useState(()=>localStorage.getItem('scamshield-theme')==='dark');
  const [user,setUser] = useState<User|null>(null);
  const [health,setHealth] = useState<Health|null>(null);
  const [message,setMessage] = useState('');
  const t = useCallback((en:string,ms:string)=>lang==='ms'?ms:en,[lang]);
  useEffect(()=>{document.documentElement.dataset.theme = dark?'dark':'light';localStorage.setItem('scamshield-theme',dark?'dark':'light')},[dark]);
  useEffect(()=>{document.documentElement.lang=lang;localStorage.setItem('scamshield-lang',lang)},[lang]);
  useEffect(()=>{api<User>('/auth/me').then(setUser).catch(()=>{});const refresh=()=>api<Health>('/health').then(setHealth).catch(()=>setHealth(null));refresh();const timer=setInterval(refresh,30000);return()=>clearInterval(timer)},[]);
  useEffect(()=>{if(message){const timer=setTimeout(()=>setMessage(''),4500);return()=>clearTimeout(timer)}},[message]);
  const logout = async()=>{await post('/auth/logout',{});setUser(null);setMessage(t('You have signed out.','Anda telah log keluar.'))};
  return <Context.Provider value={{lang,t,setLang:setLangState,dark,toggleDark:()=>setDark(!dark),user,setUser,health,toast:setMessage,logout}}>{children}{message&&<div className="toast" role="status">{message}<button onClick={()=>setMessage('')} aria-label={t('Dismiss notification','Tutup pemberitahuan')}>×</button></div>}</Context.Provider>;
}
export function useApp(){const value=useContext(Context);if(!value)throw new Error('AppProvider missing');return value}
