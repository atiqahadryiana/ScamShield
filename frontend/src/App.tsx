import {BrowserRouter,Link,Route,Routes,useLocation} from 'react-router-dom';
import {lazy,Suspense,useEffect} from 'react';
import {Loading} from './components/Common';
import {AppProvider} from './hooks/useApp';
import Shell from './layouts/Shell';
import Home from './pages/Home';
import Scanner from './pages/Scanner';
const Dashboard=lazy(()=>import('./pages/Dashboard'));
const Learn=lazy(()=>import('./pages/Learn'));
const Resources=lazy(()=>import('./pages/Resources'));
const Telegram=lazy(()=>import('./pages/Telegram'));
const About=lazy(()=>import('./pages/About'));
const Privacy=lazy(()=>import('./pages/Privacy'));
const Login=lazy(()=>import('./pages/Login'));
const History=lazy(()=>import('./pages/History'));
const Admin=lazy(()=>import('./pages/Admin'));
function PageTitle(){const {pathname}=useLocation();useEffect(()=>{const label=pathname==='/'?'Your digital safety companion':pathname.slice(1).replaceAll('-',' ');document.title=`${label.charAt(0).toUpperCase()+label.slice(1)} · ScamShield AI`},[pathname]);return null}
export default function App(){return <AppProvider><BrowserRouter><PageTitle/><Suspense fallback={<Loading/>}><Routes><Route element={<Shell/>}><Route index element={<Home/>}/><Route path="scan" element={<Scanner/>}/><Route path="url-checker" element={<Scanner/>}/><Route path="screenshot" element={<Scanner/>}/><Route path="dashboard" element={<Dashboard/>}/><Route path="learn" element={<Learn/>}/><Route path="telegram" element={<Telegram/>}/><Route path="resources" element={<Resources/>}/><Route path="about" element={<About/>}/><Route path="business" element={<About/>}/><Route path="privacy" element={<Privacy/>}/><Route path="login" element={<Login/>}/><Route path="history" element={<History/>}/><Route path="admin" element={<Admin/>}/><Route path="*" element={<div className="panel dashboard-empty"><h1>Page not found</h1><Link className="button primary" to="/">Back to overview</Link></div>}/></Route></Routes></Suspense></BrowserRouter></AppProvider>}
