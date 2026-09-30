// QR scanner that works with the front camera: tries the frame as-is, then mirrored, and jsQR
// also tries black/white inverted. The chosen camera is remembered on this phone.
(function () {
  const script = document.currentScript;
  const KEY = "stockcount.camera";
  let camera = script.dataset.camera;
  try { camera = localStorage.getItem(KEY) || camera; } catch (e) { /* private mode */ }

  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const status = document.getElementById("status");
  const camName = document.getElementById("cam-name");
  let stream = null;
  let running = false;

  // our labels hold https://liff.line.me/<id>?loc=L0301 or …/loc/L0301; a bare "L0301" also works
  function slotFrom(text) {
    const m = /(?:loc[=/])?\b([LR]\d{4})\b/i.exec(text);
    return m ? m[1].toUpperCase() : null;
  }

  function read(mirrored) {
    const w = canvas.width, h = canvas.height;
    ctx.save();
    if (mirrored) { ctx.translate(w, 0); ctx.scale(-1, 1); }
    ctx.drawImage(video, 0, 0, w, h);
    ctx.restore();
    return jsQR(ctx.getImageData(0, 0, w, h).data, w, h, { inversionAttempts: "attemptBoth" });
  }

  function go(code) {
    status.textContent = "เจอช่อง " + code + " กำลังเปิด…";
    stop();
    location.href = "/loc/" + code;
  }

  function tick() {
    if (!stream) { running = false; return; }
    if (video.readyState >= 2 && video.videoWidth) {
      const scale = Math.min(1, 640 / Math.max(video.videoWidth, video.videoHeight));
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      const hit = read(false) || read(true);
      if (hit) {
        const code = slotFrom(hit.data);
        if (code) return go(code);
        status.textContent = "QR นี้ไม่ใช่ป้ายช่อง: " + hit.data.slice(0, 40);
      }
    }
    requestAnimationFrame(tick);
  }

  function stop() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = null;
  }

  async function start() {
    stop();
    camName.textContent = camera === "front" ? "กล้องหน้า" : "กล้องหลัง";
    video.classList.toggle("mirror", camera === "front");
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: camera === "front" ? "user" : "environment" },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      status.textContent = "ส่องไปที่ QR ของช่อง";
      if (!running) { running = true; requestAnimationFrame(tick); }
    } catch (e) {
      status.textContent = "เปิดกล้องไม่ได้ (" + e.name + ") — แตะช่องบนแผนผัง หรือพิมพ์รหัสช่องแทน";
    }
  }

  document.getElementById("switch").addEventListener("click", () => {
    camera = camera === "front" ? "back" : "front";
    try { localStorage.setItem(KEY, camera); } catch (e) { /* private mode */ }
    start();
  });

  document.getElementById("manual").addEventListener("submit", (event) => {
    event.preventDefault();
    const code = slotFrom(event.target.code.value.trim());
    if (code) go(code);
    else status.textContent = "รหัสช่องต้องเป็นแบบ L0301 / R0101";
  });

  start();
})();
