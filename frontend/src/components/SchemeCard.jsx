import { useLang, speak, hostname, cx } from '../lib'
import { Button, btnClass } from './ui'

const BADGE = {
  eligible: 'bg-ok-bg text-ok',
  likely: 'bg-warn-bg text-warn',
  near_miss: 'bg-info-bg text-info',
}
export const Badge = ({ className, ...p }) =>
  <span className={cx('inline-block px-2.5 py-0.5 rounded-full text-xs font-bold mr-1.5', className)} {...p} />

function Details({ title, children }) {
  return (
    <details className="mt-2 group">
      <summary className="cursor-pointer text-teal font-semibold">{title}</summary>
      {children}
    </details>
  )
}

export default function SchemeCard({ s }) {
  const { t, lang } = useLang()
  const hi = lang === 'hi'
  const name = hi ? (s.name_hi || s.name) : s.name
  const benefit = hi ? (s.benefit_hi || s.benefit) : s.benefit
  const badgeKey = s.status === 'eligible' ? 'eligible' : s.status === 'likely' ? 'likely' : 'near'

  return (
    <div className="border border-line rounded-2xl bg-white p-3.5 my-3">
      <div>
        <Badge className={BADGE[s.status]}>{t[badgeKey]}</Badge>
        <Badge className="bg-neutral-100 text-neutral-600 font-semibold">{t.level[s.level]}</Badge>
      </div>
      <h3 className="mt-1.5 text-[17px] font-bold">{name}</h3>
      <div className="my-2 text-[15px]">{benefit}</div>

      {s.near_miss && (
        <div className="bg-info-bg rounded-xl px-3 py-2.5 text-sm my-2">
          💡 {hi ? (s.near_miss.hi || s.near_miss.en) : s.near_miss.en}
        </div>
      )}
      {s.needs_state_verification && (
        <div className="bg-warn-bg rounded-xl px-3 py-2 text-[13px] my-2">⚠️ {t.verify}</div>
      )}

      {s.passed.length > 0 && (
        <Details title={t.why}>
          <ul className="mt-1.5 pl-5 text-[13px] text-muted space-y-0.5">
            {s.passed.map((x, i) => <li key={'p' + i}>✓ {x}</li>)}
            {s.unknown.map((x, i) => <li key={'u' + i}>? {x}</li>)}
          </ul>
        </Details>
      )}
      <Details title={t.docs}>
        <ul className="mt-1.5 pl-5 text-sm list-disc">{s.documents.map((d, i) => <li key={i}>{d}</li>)}</ul>
      </Details>
      <Details title={t.steps}>
        <ol className="mt-1.5 pl-5 text-sm list-decimal">{s.steps.map((d, i) => <li key={i}>{d}</li>)}</ol>
        <div className="text-muted text-[13px] mt-1.5">{t.deadline}: {s.deadline}</div>
      </Details>

      <div className="flex flex-wrap items-center gap-2.5 mt-2.5">
        <a className={btnClass('primary', 'sm')} href={s.apply_url} target="_blank" rel="noopener noreferrer">
          {t.apply} ↗
        </a>
        <Button variant="alt" size="sm" onClick={() => speak(`${name}. ${benefit}`, lang)}>{t.listen}</Button>
        <span className="text-muted text-[13px]">{hostname(s.apply_url)}</span>
      </div>
    </div>
  )
}
