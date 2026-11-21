const CACHE='schemesaathi-v2';
const SHELL=['/','/manifest.json','/icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim();});
const put=(req,res)=>{const c=res.clone();caches.open(CACHE).then(ch=>ch.put(req,c));return res;};
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.origin!==location.origin)return;
  // API calls and page loads: network first, fall back to the last cached copy (offline-friendly).
  // Page loads must be network-first so a new build's index.html (with new hashed asset names) is picked up.
  if(u.pathname.startsWith('/api/')||e.request.mode==='navigate'){
    e.respondWith(fetch(e.request).then(r=>put(e.request,r)).catch(()=>caches.match(e.request).then(m=>m||caches.match('/'))));
    return;
  }
  // Hashed build assets never change, so cache-first is safe.
  e.respondWith(caches.match(e.request).then(m=>m||fetch(e.request).then(r=>r.ok?put(e.request,r):r)));
});
