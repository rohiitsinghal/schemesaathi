import { useState } from 'react'
import { useLang, api } from '../lib'
import { Button, Card, Field, Grid, Select, TriSelect, inputClass, stateOptions } from './ui'
import Banner from './Banner'
import SchemeCard from './SchemeCard'

const emptyMember = () => ({ name: '', age: '', gender: '', occupation: '', land_acres: '', has_bank_account: '' })

const DEMO_HH = { state: 'bihar', rural: true, bpl: true, annual_income: 90000, owns_pucca_house: false, income_tax_payer: false }
const DEMO_MEMBERS = [
  { name: 'Ramesh', age: '45', gender: 'male', occupation: 'farmer', land_acres: '1.5', has_bank_account: '1' },
  { name: 'Sunita', age: '40', gender: 'female', occupation: 'homemaker', land_acres: '', has_bank_account: '1' },
  { name: 'Meera', age: '19', gender: 'female', occupation: 'student', land_acres: '', has_bank_account: '0' },
  { name: 'Dadi', age: '68', gender: 'female', occupation: '', land_acres: '', has_bank_account: '1' },
]

function cleanMember(m) {
  const o = {}
  if (m.name) o.name = m.name
  if (m.age !== '') o.age = +m.age
  if (m.gender) o.gender = m.gender
  if (m.occupation) o.occupation = m.occupation
  if (m.land_acres !== '') o.land_acres = +m.land_acres
  if (m.has_bank_account !== '') o.has_bank_account = m.has_bank_account === '1'
  return o
}

export default function FamilyTab() {
  const { t } = useLang()
  const [hh, setHh] = useState({ rural: true, bpl: true })
  const [members, setMembers] = useState([emptyMember()])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(false)

  const setH = (k, v) => setHh(h => ({ ...h, [k]: v }))
  const setM = (i, k, v) => setMembers(ms => ms.map((m, j) => j === i ? { ...m, [k]: v } : m))

  async function run(household = hh, mems = members) {
    const clean = Object.fromEntries(Object.entries(household).filter(([, v]) => v !== undefined && v !== ''))
    try { setResult(await api('/api/family', { household: clean, members: mems.map(cleanMember) })); setError(false) }
    catch { setError(true) }
  }

  function loadDemo() { setHh(DEMO_HH); setMembers(DEMO_MEMBERS); run(DEMO_HH, DEMO_MEMBERS) }

  return (
    <section>
      <Card>
        <h3 className="font-bold mb-1">{t.famH}</h3>
        <p className="text-muted text-[13px] mb-2.5">{t.famP}</p>
        <Grid>
          <Field label={t.hhState}><Select value={hh.state} onChange={v => setH('state', v || undefined)} options={stateOptions} /></Field>
          <Field label={t.hhRural}><TriSelect value={hh.rural} onChange={v => setH('rural', v)} yes={t.village} no={t.city} /></Field>
          <Field label={t.hhBpl}><TriSelect value={hh.bpl} onChange={v => setH('bpl', v)} /></Field>
          <Field label={t.hhIncome}>
            <input type="number" step="1000" className={inputClass} value={hh.annual_income ?? ''}
              onChange={e => setH('annual_income', e.target.value === '' ? undefined : +e.target.value)} />
          </Field>
          <Field label={t.hhHouse}><TriSelect value={hh.owns_pucca_house} onChange={v => setH('owns_pucca_house', v)} /></Field>
          <Field label={t.fieldsLabel.income_tax_payer}><TriSelect value={hh.income_tax_payer} onChange={v => setH('income_tax_payer', v)} /></Field>
        </Grid>

        {members.map((m, i) => (
          <div key={i} className="border border-dashed border-field rounded-2xl p-3 my-2.5">
            <Grid>
              <Field label={t.name}>
                <input className={inputClass} value={m.name} placeholder={`${t.member} ${i + 1}`} onChange={e => setM(i, 'name', e.target.value)} />
              </Field>
              <Field label={t.age}>
                <input type="number" className={inputClass} value={m.age} onChange={e => setM(i, 'age', e.target.value)} />
              </Field>
              <Field label={t.gender}>
                <Select value={m.gender} onChange={v => setM(i, 'gender', v)} options={[['male', t.male], ['female', t.female]]} />
              </Field>
              <Field label={t.job}>
                <Select value={m.occupation} onChange={v => setM(i, 'occupation', v)} options={Object.entries(t.occ)} />
              </Field>
              <Field label={t.acres}>
                <input type="number" step="0.5" className={inputClass} value={m.land_acres} onChange={e => setM(i, 'land_acres', e.target.value)} />
              </Field>
              <Field label={t.bank}>
                <Select value={m.has_bank_account} onChange={v => setM(i, 'has_bank_account', v)} options={[['1', t.yes], ['0', t.no]]} />
              </Field>
            </Grid>
            {members.length > 1 && (
              <Button variant="alt" size="sm" className="mt-2" onClick={() => setMembers(ms => ms.filter((_, j) => j !== i))}>
                {t.remove}
              </Button>
            )}
          </div>
        ))}

        <div className="flex flex-wrap items-center gap-2.5 mt-2.5">
          <Button variant="alt" size="sm" onClick={() => setMembers(ms => [...ms, emptyMember()])}>{t.addMember}</Button>
          <Button variant="saffron" size="sm" onClick={loadDemo}>{t.demoFam}</Button>
          <Button onClick={() => run()}>{t.goFam}</Button>
        </div>
      </Card>

      {error && <Card>{t.err}</Card>}
      {!error && result && (
        <>
          <Banner totals={result.totals} title={t.total} />
          {result.members.map((m, i) => {
            const shown = m.schemes.filter(s => s.status !== 'near_miss')
            const near = m.schemes.filter(s => s.status === 'near_miss')
            const all = shown.concat(near)
            return (
              <div key={i}>
                <h2 className="text-lg font-bold mt-5 mb-1 text-teal">{m.name} ({shown.length})</h2>
                {all.length ? all.map(s => <SchemeCard key={s.id} s={s} />) : <Card className="text-muted">{t.none}</Card>}
              </div>
            )
          })}
        </>
      )}
    </section>
  )
}
