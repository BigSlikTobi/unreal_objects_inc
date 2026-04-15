import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { DashboardApp } from './DashboardApp';
import faviconUrl from './assets/favicon.svg';

document.documentElement.classList.add('dark');

// Set favicon from assets
const link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
if (link) link.href = faviconUrl;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DashboardApp />
  </StrictMode>,
);
