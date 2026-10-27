import type {ReactNode} from 'react';
import {AlertCircle, ArrowUpRight, RotateCw, ShieldCheck} from 'lucide-react';
import {useApp} from '../hooks/useApp';
export function Brand(){return <span className="brand"><span className="brand-icon"><ShieldCheck size={25}/></span><span>ScamShield<span className="brand-ai">AI</span><small>YOUR DIGITAL SAFETY COMPANION</small></span></span>}
export function PageHeading({eyebrow,title,description,action}:{eyebrow:string;title:string;description:string;action?:ReactNode}){return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>}
export function ErrorBox({message,retry}:{message:string;retry?:()=>void}){const {t}=useApp();return <div className="error-box" role="alert"><AlertCircle size={20}/><div><strong>{t('Something needs attention','Sesuatu memerlukan perhatian')}</strong><p>{message}</p>{retry&&<button className="text-link" onClick={retry}><RotateCw size={14}/>{t('Try again','Cuba lagi')}</button>}</div></div>}
export function Loading(){const {t}=useApp();return <div role="status" aria-label={t('Loading','Memuatkan')} className="space-y-4"><div className="skeleton h-24"/><div className="skeleton h-64"/></div>}
export function ExternalLink({href,children,className=''}:{href:string;children:ReactNode;className?:string}){return <a href={href} target="_blank" rel="noopener noreferrer" className={className}>{children}<ArrowUpRight size={16}/><span className="sr-only"> (opens in a new tab)</span></a>}
