import { useState } from 'react'
import { useLang, BOOL_FIELDS } from '../lib'
import { Button, Select, inputClass, stateOptions } from './ui'

/* One follow-up question from the engine, with the right control for its field. */
export default function Followup({ q, onAnswer }) {
  const { t, lang } = useLang()
  const [num, setNum] = useState('')
  const f = q.field
  const pair = (a, b) => (
    <>
      <Button size="sm" onClick={() => onAnswer(f, a[0])}>{a[1]}</Button>
      <Button size="sm" variant="alt" onClick={() => onAnswer(f, b[0])}>{b[1]}</Button>
    </>
  )

  let ctl
  if (BOOL_FIELDS.has(f)) ctl = pair([true, t.yes], [false, t.no])
  else if (f === 'rural') ctl = pair([true, t.village], [false, t.city])
  else if (f === 'gender') ctl = pair(['female', t.female], ['male', t.male])
  else if (f === 'category') ctl = Object.entries(t.cat).map(([k, v]) =>
    <Button key={k} size="sm" variant="alt" onClick={() => onAnswer(f, k)}>{v}</Button>)
  else if (f === 'occupation' || f === 'state') ctl = (
    <Select className="max-w-[260px]" placeholder="…" value=""
      options={f === 'state' ? stateOptions : Object.entries(t.occ)}
      onChange={v => v && onAnswer(f, v)} />
  )
  else ctl = (
    <>
      <input type="number" className={inputClass + ' max-w-[160px]'} value={num} onChange={e => setNum(e.target.value)}
        placeholder={f === 'annual_income' ? '₹/year' : f === 'land_acres' ? 'acres' : ''} />
      <Button size="sm" onClick={() => num !== '' && onAnswer(f, +num)}>{t.set}</Button>
    </>
  )

  return (
    <div className="bg-warn-bg border border-[#f0d9a4] rounded-2xl p-3 my-3">
      <span className="text-muted text-[13px]">💡 {t.askMore} (+{q.unlocks})</span>
      <div className="font-bold mt-1">{lang === 'hi' ? q.q_hi : q.q_en}</div>
      <div className="flex flex-wrap items-center gap-2.5 mt-2">{ctl}</div>
    </div>
  )
}
