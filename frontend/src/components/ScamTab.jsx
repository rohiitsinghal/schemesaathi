import { useState } from 'react'
import { useLang, api, cx } from '../lib'
import { Button, Card, Chip, Chips, inputClass } from './ui'
import { Badge } from './SchemeCard'

const RISK = { high: 'bg-bad-bg text-bad', medium: 'bg-warn-bg text-warn', low: 'bg-ok-bg text-ok' }
const VERDICT = { official: 'bg-ok-bg text-ok', suspicious: 'bg-bad-bg text-bad' }

export default function ScamTab() {
  const { t } = useLang()
  const [text, setText] = useState('')
  const [r, setR] = useState(null)
  const [error, setError] = useState(false)

  async function run(raw = text) {
    const s = raw.trim(); if (!s) return
    try { setR(await api('/api/scam', { text: s })); setError(false) }
    catch { setError(true) }
  }

  return (
    <section>
      <Card>
        <h3 className="font-bold mb-1">{t.scH}</h3>
        <p className="text-muted text-[13px] mb-2.5">{t.scP}</p>
        <textarea className={cx(inputClass, 'min-h-[92px] resize-y')} placeholder={t.scPh}
          value={text} onChange={e => setText(e.target.value)} />
        <Chips>
          {t.scEx.map(([label, sample], i) => (
            <Chip key={i} onClick={() => { setText(sample); run(sample) }}>{label}</Chip>
          ))}
        </Chips>
        <div className="mt-3"><Button onClick={() => run()}>{t.scGo}</Button></div>

        {error && <Card>{t.err}</Card>}
        {!error && r && (
          <div className={cx('rounded-2xl p-3.5 mt-3', RISK[r.risk])}>
            <b className="text-[17px]">{t.risk[r.risk]}</b> <span className="text-muted text-[13px]">({r.score}/100)</span>
            {r.flags.length > 0 && <ul className="list-disc pl-5 mt-1">{r.flags.map((x, i) => <li key={i}>{x}</li>)}</ul>}
            {r.urls.map((u, i) => (
              <div key={i} className="mt-2">
                <b>{u.host || u.url}</b> — <Badge className={VERDICT[u.verdict] ?? 'bg-warn-bg text-warn'}>{t.verdictL[u.verdict]}</Badge>
                <ul className="pl-5 text-[13px] text-muted list-disc">{u.reasons.map((x, j) => <li key={j}>{x}</li>)}</ul>
              </div>
            ))}
            <ul className="mt-2.5 text-ink text-sm list-disc pl-5">{r.advice.map((x, i) => <li key={i}>{x}</li>)}</ul>
          </div>
        )}
      </Card>
    </section>
  )
}
