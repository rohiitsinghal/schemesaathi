import { useLang, inr } from '../lib'

const Stat = ({ value, label }) => (
  <div>
    <b className="block text-2xl">{value}</b>
    <span className="text-xs opacity-85">{label}</span>
  </div>
)

export default function Banner({ totals: tot, title }) {
  const { t, lang } = useLang()
  const hi = lang === 'hi'
  const pot = []
  if (tot.potential_yearly_cash) pot.push(inr(tot.potential_yearly_cash) + ' / ' + (hi ? 'वर्ष' : 'yr'))
  if (tot.potential_one_time_cash) pot.push(inr(tot.potential_one_time_cash) + ' ' + (hi ? 'एकमुश्त' : 'one-time'))
  if (tot.potential_insurance_cover) pot.push(inr(tot.potential_insurance_cover) + ' ' + t.cover)

  return (
    <div className="bg-gradient-to-br from-teal to-[#1b6b5f] text-white rounded-2xl p-[18px] my-3.5">
      <h2 className="text-[15px] font-semibold opacity-90 mb-0.5">{title}</h2>
      <div className="grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-3 mt-2.5">
        {!!tot.yearly_cash && <Stat value={inr(tot.yearly_cash)} label={t.yearly} />}
        {!!tot.one_time_cash && <Stat value={inr(tot.one_time_cash)} label={t.oneTime} />}
        {!!tot.insurance_cover && <Stat value={inr(tot.insurance_cover)} label={t.cover} />}
        <Stat value={tot.count_eligible} label={t.eligible} />
        {!!tot.count_likely && <Stat value={tot.count_likely} label={t.likely} />}
      </div>
      {pot.length > 0 && (
        <div className="text-[13px] mt-2.5 opacity-95">＋ {t.potential} <b>{pot.join(' · ')}</b></div>
      )}
      <div className="text-xs opacity-80 mt-2.5">{t.note}</div>
    </div>
  )
}
