import { createContext, useContext, useEffect, useRef } from 'react';
import { ArrowRight, AlertCircle, X, LoaderCircle, Check, Activity } from 'lucide-react';

export const LocaleContext = createContext();
export const useLocale = () => useContext(LocaleContext);
export function Brand({ light = false }) { return <div className={`brand ${light ? 'brand-light' : ''}`}><span className="brand-symbol"><Activity size={23} strokeWidth={2.4}/></span><span>smart<span className="brand-pe">pe</span><span className="brand-dot">.</span></span></div>; }
export function Button({ children, icon: Icon, variant = 'primary', busy, className = '', ...props }) { return <button className={`button ${variant} ${className}`} {...props} disabled={busy || props.disabled}>{busy ? <LoaderCircle className="spin" size={17}/> : Icon && <Icon size={17}/>}<span>{children}</span></button>; }
export function Empty({ icon: Icon = Activity, title, text, action }) { return <div className="empty"><span className="empty-icon"><Icon size={30}/></span><h3>{title}</h3><p>{text}</p>{action}</div>; }
export function Loading() { return <div className="skeleton-grid" aria-label="Loading" aria-busy="true"><div className="skeleton wide"/><div className="skeleton"/><div className="skeleton"/><div className="skeleton wide"/></div>; }
export function ErrorMessage({ error, retry }) { const { t } = useLocale(); return <div className="error-message" role="alert"><AlertCircle size={20}/><div><strong>{t('Could not load this view', 'Не удалось загрузить данные')}</strong><p>{error?.message || String(error)}</p>{retry && <Button variant="secondary" onClick={retry}>{t('Try again', 'Попробовать снова')}</Button>}</div></div>; }
export function QueryState({ query, children }) { if (query.isPending) return <Loading/>; if (query.isError) return <ErrorMessage error={query.error} retry={query.refetch}/>; return children(query.data); }
export function Stat({ label, value, suffix, icon: Icon, note, color = 'mint' }) { return <article className="stat"><div className="stat-head"><span>{label}</span><span className={`stat-icon ${color}`}><Icon size={18}/></span></div><div className="stat-value">{value}<small>{suffix}</small></div>{note && <p>{note}</p>}</article>; }
export function SectionHeading({ eyebrow, title, text, action }) { return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2>{text && <p>{text}</p>}</div>{action}</div>; }
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef();
  const { t } = useLocale();
  useEffect(() => { const dialog = ref.current; dialog.showModal(); const handler = () => onClose(); dialog.addEventListener('cancel', handler); return () => { dialog.removeEventListener('cancel', handler); dialog.close(); }; }, []);
  return <dialog ref={ref} className={`modal ${wide ? 'modal-wide' : ''}`} aria-labelledby="dialog-title" onClick={event => { if (event.target === ref.current) onClose(); }}><div className="modal-head"><h2 id="dialog-title">{title}</h2><button type="button" className="icon-button" onClick={onClose} aria-label={t('Close', 'Закрыть')}><X size={20}/></button></div>{children}</dialog>;
}
export function Field({ label, children, ...props }) { return <label className="field"><span>{label}</span>{children || <input {...props}/>}</label>; }
export function Badge({ status }) { const { t } = useLocale(); const names = { SCHEDULED: t('Scheduled', 'Запланировано'), COMPLETED: t('Completed', 'Завершено'), IN_PROGRESS: t('In progress', 'В процессе'), SKIPPED: t('Skipped', 'Пропущено'), DISCARDED: t('Discarded', 'Отменено'), active: t('Active', 'Активно'), recovered: t('Recovered', 'Восстановлено') }; return <span className={`badge status-${status?.toLowerCase()}`}>{names[status] || status}</span>; }
export function Ring({ value, size = 112, label, detail }) { const safe = Math.max(0, Math.min(100, value || 0)); return <div className="ring" style={{ width: size, height: size }}><svg viewBox="0 0 120 120" aria-hidden="true"><circle cx="60" cy="60" r="50" className="ring-track"/><circle cx="60" cy="60" r="50" className="ring-value" strokeDasharray={`${safe * Math.PI} 314.16`} transform="rotate(-90 60 60)"/></svg><div><strong>{label ?? `${Math.round(safe)}%`}</strong>{detail && <small>{detail}</small>}</div></div>; }
export function Notice({ children, success = false }) { return <div className={`notice ${success ? 'success' : ''}`} role="status">{success ? <Check size={17}/> : <AlertCircle size={17}/>}<span>{children}</span></div>; }
export function TextLink({ children, onClick }) { return <button className="text-link" onClick={onClick}>{children}<ArrowRight size={16}/></button>; }
