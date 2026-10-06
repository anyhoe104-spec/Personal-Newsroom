/* Relative URLs also work when GitHub Pages hosts the app in a repository path. */
if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  navigator.serviceWorker.register('./sw.js').catch(() => {
    // The reader remains usable online when offline installation is unavailable.
    console.info('Offline installation unavailable');
  });
}
let installPrompt;
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault(); installPrompt = event;
  document.getElementById('installApp').hidden = false;
});
document.getElementById('installApp').addEventListener('click', async () => {
  if (!installPrompt) return;
  await installPrompt.prompt(); await installPrompt.userChoice;
  installPrompt = null; document.getElementById('installApp').hidden = true;
});

// A failed server connection can still report navigator.onLine=true.
async function checkCachedConnection() {
  try {
    const response = await fetch('./manifest.webmanifest', { cache: 'no-store' });
    document.getElementById('offline').hidden = navigator.onLine && response.headers.get('X-Newsroom-Offline') !== '1';
  } catch { document.getElementById('offline').hidden = false; }
}
checkCachedConnection();
window.addEventListener('online', checkCachedConnection);
window.addEventListener('offline', () => {
  document.getElementById('offline').hidden = false;
});
