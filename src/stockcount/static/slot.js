// Slot page helpers: camera choice for the photo, one-tap-one-save, voice input (Thai/English).
(function () {
  const script = document.currentScript;
  const code = script.dataset.code;
  const CAMERA_KEY = "stockcount.camera";
  let camera = script.dataset.camera;
  try { camera = localStorage.getItem(CAMERA_KEY) || camera; } catch (e) { /* private mode: use the default */ }

  // the photo button opens the camera ณัฑฒ์ chose on the scan page (front when the back one is broken)
  const photo = document.getElementById("photo");
  if (photo) {
    photo.setAttribute("capture", camera === "front" ? "user" : "environment");
    photo.addEventListener("change", () => {
      document.getElementById("photo-name").textContent = photo.files[0] ? "📎 แนบรูปแล้ว: " + photo.files[0].name : "";
    });
  }

  const form = document.getElementById("count-form");
  if (form) {
    form.addEventListener("submit", () => {
      const button = form.querySelector("button[type=submit]");
      if (button) { button.disabled = true; button.textContent = "กำลังบันทึก…"; }
    });
  }

  // voice: the browser's own speech recognition, when the in-app browser has it
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const voice = document.getElementById("voice");
  const langButton = document.getElementById("voice-lang");
  const hint = document.getElementById("voice-hint");
  if (!Recognition || !voice) return;
  voice.hidden = false;
  langButton.hidden = false;
  let lang = "th-TH";
  langButton.addEventListener("click", () => {
    lang = lang === "th-TH" ? "en-US" : "th-TH";
    langButton.textContent = lang === "th-TH" ? "ไทย" : "EN";
  });

  voice.addEventListener("click", () => {
    const rec = new Recognition();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    voice.textContent = "🎙️ กำลังฟัง…";
    rec.onresult = async (event) => {
      const text = event.results[0][0].transcript;
      hint.textContent = "ได้ยิน: " + text;
      try {
        const res = await fetch("/loc/" + encodeURIComponent(code) + "/voice", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        const data = await res.json();
        const found = Object.entries(data.counts || {});
        found.forEach(([sku, qty]) => {
          const input = document.querySelector('input[data-sku="' + sku + '"]');
          if (input) { input.value = qty; input.classList.add("filled"); }
        });
        if (found.length) document.getElementById("input_method").value = "voice";
        hint.textContent += found.length ? " → เติม " + found.length + " ช่อง ตรวจแล้วกดบันทึก" : " → ไม่เจอชื่อสินค้าของช่องนี้";
      } catch (e) {
        hint.textContent += " → ส่งไม่สำเร็จ พิมพ์แทนได้";
      }
    };
    rec.onerror = () => { hint.textContent = "ฟังไม่ทัน ลองอีกครั้ง หรือพิมพ์แทน"; };
    rec.onend = () => { voice.textContent = "🎤 พูดยอด"; };
    rec.start();
  });
})();
