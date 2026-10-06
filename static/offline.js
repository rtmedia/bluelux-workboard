let checking = false;
async function reconnect() {
  if (checking) return;
  checking = true;
  try {
    const response = await fetch('/api/health', {cache:'no-store', signal:AbortSignal.timeout(3000)});
    const health = await response.json();
    if (response.ok && health.app === 'workboard') { location.replace('/'); return; }
  } catch {}
  document.querySelector('#recoveryStatus').textContent = 'Still waiting for the local server. Checking again shortly…';
  checking = false;
}
document.querySelector('#retry').addEventListener('click', reconnect);
setInterval(reconnect, 5000); reconnect();
