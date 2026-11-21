import { createContext, useContext } from 'react'

export const STATES = ["andhra pradesh","assam","bihar","chhattisgarh","delhi","gujarat","haryana","himachal pradesh","jharkhand","karnataka","kerala","madhya pradesh","maharashtra","odisha","punjab","rajasthan","tamil nadu","telangana","uttar pradesh","uttarakhand","west bengal"]
export const BOOL_FIELDS = new Set(["bpl","owns_pucca_house","has_bank_account","income_tax_payer","girl_child_under10","disabled","pregnant","epfo_member","has_lpg","top20_percentile"])

export const inr = n => '₹' + Math.round(n).toLocaleString('en-IN')
export const cap = s => s.replace(/\b\w/g, c => c.toUpperCase())
export const cx = (...c) => c.filter(Boolean).join(' ')

export async function api(path, body) {
  const r = await fetch(path, body
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    : undefined)
  if (!r.ok) throw new Error(r.status)
  return r.json()
}

export function speak(text, lang) {
  if (!('speechSynthesis' in window)) return
  speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = lang === 'hi' ? 'hi-IN' : 'en-IN'
  speechSynthesis.speak(u)
}

export const hostname = url => { try { return new URL(url).hostname } catch { return '' } }

/* Language context: { lang, t, setLang } */
export const LangContext = createContext(null)
export const useLang = () => useContext(LangContext)

/* "1"/"0"/"" <-> true/false/undefined for tri-state selects */
export const triToStr = v => v === true ? '1' : v === false ? '0' : ''
export const strToTri = s => s === '' ? undefined : s === '1'
