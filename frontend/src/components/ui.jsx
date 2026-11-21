import { cx, useLang, STATES, cap, triToStr, strToTri } from '../lib'

const VARIANTS = {
  primary: 'bg-teal text-white hover:bg-teal2 border border-teal',
  alt: 'bg-white text-teal border border-teal hover:bg-sand',
  saffron: 'bg-saffron text-teal border border-saffron hover:brightness-95',
}
const SIZES = {
  md: 'px-[18px] py-[11px] rounded-xl',
  sm: 'px-3 py-1.5 text-[13px] rounded-[10px]',
}
export const btnClass = (variant = 'primary', size = 'md', className = '') =>
  cx('inline-block font-bold cursor-pointer no-underline transition-colors', VARIANTS[variant], SIZES[size], className)

export function Button({ variant, size, className, ...props }) {
  return <button type="button" className={btnClass(variant, size, className)} {...props} />
}

export const Card = ({ className, ...p }) =>
  <div className={cx('bg-white border border-line rounded-2xl p-4 my-3.5', className)} {...p} />

export const Chip = ({ className, ...p }) =>
  <button type="button" className={cx('bg-sand border border-line rounded-full px-3 py-1 text-[13px] cursor-pointer hover:border-saffron', className)} {...p} />

export const Chips = ({ className, ...p }) => <div className={cx('flex flex-wrap gap-2 mt-2.5', className)} {...p} />

export const inputClass = 'w-full px-3 py-2.5 border border-field rounded-xl bg-white text-ink focus:outline-2 focus:outline-saffron'

export const Field = ({ label, children }) => (
  <label className="block">
    <span className="block text-[13px] text-muted mb-1">{label}</span>
    {children}
  </label>
)

export const Grid = ({ className, ...p }) =>
  <div className={cx('grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-2.5', className)} {...p} />

/* Generic select with a leading "Not sure" option. options: [[value, label]] */
export function Select({ value, onChange, options, placeholder, className }) {
  const { t } = useLang()
  return (
    <select className={cx(inputClass, className)} value={value ?? ''} onChange={e => onChange(e.target.value)}>
      <option value="">{placeholder ?? t.unknown}</option>
      {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  )
}

/* Yes / No / Not sure, bound to true / false / undefined */
export function TriSelect({ value, onChange, yes, no }) {
  const { t } = useLang()
  return <Select value={triToStr(value)} onChange={s => onChange(strToTri(s))}
    options={[['1', yes ?? t.yes], ['0', no ?? t.no]]} />
}

export const stateOptions = STATES.map(s => [s, cap(s)])
