import { useEffect, useMemo, useState } from 'react'
import { T } from './i18n'
import { LangContext, cx } from './lib'
import FindTab from './components/FindTab'
import FamilyTab from './components/FamilyTab'
import ScamTab from './components/ScamTab'

const readLang = () => { try { return localStorage.getItem('ss_lang') || 'en' } catch { return 'en' } }

export default function App() {
  const [lang, setLangState] = useState(readLang)
  const [tab, setTab] = useState('find')
  const t = T[lang]

  const setLang = l => { setLangState(l); try { localStorage.setItem('ss_lang', l) } catch { /* private mode */ } }
  useEffect(() => { document.documentElement.lang = lang }, [lang])
  const ctx = useMemo(() => ({ lang, t, setLang }), [lang])

  const tabs = [['find', t.tfind], ['family', t.tfam], ['scam', t.tscam]]
  const langBtn = (code, label) => (
    <button type="button" onClick={() => setLang(code)}
      className={cx('px-3 py-1.5 rounded-full text-[13px] border cursor-pointer',
        lang === code ? 'bg-saffron text-teal border-saffron font-bold' : 'bg-transparent text-white border-white/45')}>
      {label}
    </button>
  )

  return (
    <LangContext.Provider value={ctx}>
      <header className="bg-teal text-white px-4 py-3.5 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3 max-w-[880px] mx-auto">
          <div className="flex items-center gap-2.5 font-extrabold text-xl">
            <img src="/icon.svg" alt="" className="w-8 h-8" />
            <div>
              SchemeSaathi
              <small className="block font-normal text-xs opacity-85 -mt-0.5">{t.tag}</small>
            </div>
          </div>
          <div className="flex gap-1">{langBtn('en', 'EN')}{langBtn('hi', 'हिन्दी')}</div>
        </div>
      </header>

      <main className="max-w-[880px] mx-auto px-4">
        <div className="pt-[18px] pb-1">
          <h1 className="text-[26px] leading-tight font-bold mb-1.5 text-teal">{t.h1}</h1>
          <p className="text-muted">{t.sub}</p>
        </div>

        <nav className="flex gap-1.5 mt-4 mb-2 overflow-x-auto">
          {tabs.map(([id, label]) => (
            <button key={id} type="button" onClick={() => setTab(id)}
              className={cx('flex-1 min-w-max px-3.5 py-2.5 rounded-xl border text-[15px] cursor-pointer',
                tab === id ? 'bg-teal text-white border-teal font-bold' : 'bg-white text-ink border-line')}>
              {label}
            </button>
          ))}
        </nav>

        {/* Keep all tabs mounted so switching doesn't lose what the user entered. */}
        <div hidden={tab !== 'find'}><FindTab /></div>
        <div hidden={tab !== 'family'}><FamilyTab /></div>
        <div hidden={tab !== 'scam'}><ScamTab /></div>

        <div className="text-xs text-muted text-center pt-6 pb-10">{t.disc}</div>
      </main>
    </LangContext.Provider>
  )
}
