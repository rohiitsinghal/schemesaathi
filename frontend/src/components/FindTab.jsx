import { useEffect, useRef, useState } from 'react'
import { useLang, api, inr, cap, cx, triToStr, strToTri } from '../lib'
import { Button, Card, Chip, Chips, Field, Grid, Select, TriSelect, inputClass, stateOptions } from './ui'
import Banner from './Banner'
import SchemeCard from './SchemeCard'
import Followup from './Followup'

const SR = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)

function factText(t, k, v) {
  const L = t.fieldsLabel[k] || k
  let val = v
  if (typeof v === 'boolean' && k !== 'rural') val = v ? t.yes : t.no
  else if (k === 'annual_income') val = inr(v)
  else if (k === 'land_acres') val = v + ' ac'
  else if (k === 'occupation') val = t.occ[v] || v
  else if (k === 'category') val = t.cat[v] || v
  else if (k === 'gender') val = v === 'female' ? t.female : t.male
  else if (k === 'rural') val = v ? t.village : t.city
  else if (k === 'state') val = cap(v)
  return `${L}: ${val}`
}

const SectionTitle = ({ children }) => <h2 className="text-lg font-bold mt-5 mb-1 text-teal">{children}</h2>

export default function FindTab() {
  const { t, lang } = useLang()
  const [text, setText] = useState('')
  const [profile, setProfile] = useState({})
  const [match, setMatch] = useState(null)
  const [error, setError] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [listening, setListening] = useState(false)
  const [micMsg, setMicMsg] = useState(null) // null → default "tap mic" note
  const recRef = useRef(null)
  const textRef = useRef('')
  textRef.current = text

  // Re-run the engine whenever the profile changes (debounced so typing in the form doesn't spam).
  useEffect(() => {
    if (!Object.keys(profile).length) { setMatch(null); setError(false); return }
    let stale = false
    const id = setTimeout(async () => {
      try { const m = await api('/api/match', { profile }); if (!stale) { setMatch(m); setError(false) } }
      catch { if (!stale) setError(true) }
    }, 200)
    return () => { stale = true; clearTimeout(id) }
  }, [profile])

  async function findFromText(raw = textRef.current) {
    const s = raw.trim(); if (!s) return
    try {
      const r = await api('/api/parse', { text: s })
      setProfile(p => ({ ...p, ...r.profile }))
      setError(false)
    } catch { setError(true) }
  }

  const setField = (k, v) => setProfile(p => {
    const n = { ...p }
    if (v === '' || v === null || v === undefined || Number.isNaN(v)) delete n[k]; else n[k] = v
    return n
  })

  function toggleMic() {
    if (!SR) { setMicMsg(t.micNo); return }
    if (recRef.current) { recRef.current.stop(); return }
    const rec = new SR()
    rec.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'; rec.interimResults = true; rec.continuous = false
    const base = textRef.current ? textRef.current + ' ' : ''
    rec.onstart = () => { setListening(true); setMicMsg(null) }
    rec.onresult = e => setText(base + [...e.results].map(r => r[0].transcript).join(' '))
    rec.onerror = () => {}
    rec.onend = () => { setListening(false); recRef.current = null; if (textRef.current.trim()) findFromText() }
    recRef.current = rec
    rec.start()
  }

  const numField = k => (
    <input type="number" className={inputClass} value={profile[k] ?? ''}
      min={k === 'age' ? 5 : 0} max={k === 'age' ? 110 : undefined}
      step={k === 'annual_income' ? 1000 : k === 'land_acres' ? 0.5 : 1}
      onChange={e => setField(k, e.target.value === '' ? '' : +e.target.value)} />
  )

  const by = k => match.schemes.filter(s => s.status === k)
  const section = (title, arr) => arr.length > 0 && (
    <>
      <SectionTitle>{title} ({arr.length})</SectionTitle>
      {arr.map(s => <SchemeCard key={s.id} s={s} />)}
    </>
  )
  const q = match?.next_questions?.[0]
  const facts = Object.keys(profile)

  return (
    <section>
      <Card>
        <label htmlFor="said" className="block text-[13px] text-muted mb-1">{t.say}</label>
        <div className="flex gap-2.5 items-center">
          <textarea id="said" className={cx(inputClass, 'min-h-[92px] resize-y')} placeholder={t.ph}
            value={text} onChange={e => setText(e.target.value)} />
          <button type="button" title="Speak" onClick={toggleMic}
            className={cx('w-[46px] h-[46px] rounded-full flex-none text-xl cursor-pointer',
              listening ? 'bg-bad text-white animate-mic' : 'bg-saffron')}>🎤</button>
        </div>

        <Chips>
          {t.examples.map(([label, sample], i) => (
            <Chip key={i} onClick={() => { setText(sample); findFromText(sample) }}>{label}</Chip>
          ))}
        </Chips>

        <div className="flex flex-wrap items-center gap-2.5 mt-3">
          <Button onClick={() => findFromText()}>{t.go}</Button>
          <Button variant="alt" onClick={() => setShowForm(s => !s)}>{showForm ? t.formHide : t.form}</Button>
          <span className="text-muted text-[13px]">{listening ? t.listening : micMsg ?? t.micNote}</span>
        </div>

        {showForm && (
          <Grid className="mt-3.5">
            <Field label={t.fieldsLabel.age}>{numField('age')}</Field>
            <Field label={t.fieldsLabel.gender}>
              <Select value={profile.gender} onChange={v => setField('gender', v)} options={[['male', t.male], ['female', t.female]]} />
            </Field>
            <Field label={t.fieldsLabel.state}>
              <Select value={profile.state} onChange={v => setField('state', v)} options={stateOptions} />
            </Field>
            <Field label={t.fieldsLabel.occupation}>
              <Select value={profile.occupation} onChange={v => setField('occupation', v)} options={Object.entries(t.occ)} />
            </Field>
            <Field label={t.fieldsLabel.category}>
              <Select value={profile.category} onChange={v => setField('category', v)} options={Object.entries(t.cat)} />
            </Field>
            <Field label={t.hhIncome}>{numField('annual_income')}</Field>
            <Field label={t.acres}>{numField('land_acres')}</Field>
            <Field label={t.hhRural}>
              <Select value={triToStr(profile.rural)} onChange={v => setField('rural', strToTri(v))}
                options={[['1', t.village], ['0', t.city]]} />
            </Field>
            {['bpl', 'has_bank_account', 'income_tax_payer', 'owns_pucca_house'].map(k => (
              <Field key={k} label={t.fieldsLabel[k]}>
                <TriSelect value={profile[k]} onChange={v => setField(k, v)} />
              </Field>
            ))}
          </Grid>
        )}

        {facts.length > 0 && (
          <Chips className="items-center">
            <span className="text-muted text-[13px]">{t.youSaid}:</span>
            {facts.map(k => (
              <span key={k} className="bg-info-bg border border-[#c7d7fb] text-info rounded-full px-3 py-1 text-[13px]">
                {factText(t, k, profile[k])}
                <button type="button" title={t.remove} onClick={() => setField(k, undefined)}
                  className="ml-1.5 font-bold opacity-70 hover:opacity-100 cursor-pointer">×</button>
              </span>
            ))}
          </Chips>
        )}
      </Card>

      {q && <Followup key={q.field} q={q} onAnswer={setField} />}

      {error && <Card>{t.err}</Card>}
      {!error && match && (match.schemes.length ? (
        <>
          <Banner totals={match.totals} title={t.banner} />
          {section(t.secElig, by('eligible'))}
          {section(t.secLikely, by('likely'))}
          {section(t.secNear, by('near_miss'))}
        </>
      ) : <Card>{t.none}</Card>)}
    </section>
  )
}
