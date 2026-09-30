  const EN_TO_TH = {{ en_to_th|tojson }};
  const TH_TO_EN = {{ th_to_en|tojson }};
  // same rule as stockcount/keyboard.py: convert word by word, never touch plain numbers
  function convert(text, table, needs) {
    return text.split(/(\s+)/).map(t =>
      (/^\d+$/.test(t) || !needs.test(t)) ? t : [...t].map(c => table[c] ?? c).join("")
    ).join("");
  }
  (function () {
    const items = [...document.querySelectorAll("[data-search]")];
    const input = document.getElementById("q");
    const hint = document.getElementById("hint");
    if (!input) return;
    const hits = q => items.filter(el => el.dataset.search.includes(q));
    input.addEventListener("input", () => {
      const raw = input.value.trim().toLowerCase();
      items.forEach(el => el.classList.remove("hit"));
      document.body.classList.toggle("searching", raw.length > 0);
      hint.textContent = "";
      if (!raw) return;
      let found = hits(raw);
      if (!found.length) {
        for (const alt of [convert(raw, EN_TO_TH, /[a-z]/), convert(raw, TH_TO_EN, /[฀-๿]/)]) {
          if (alt !== raw && hits(alt).length) {
            found = hits(alt);
            hint.textContent = "ค้นหาเป็น: " + alt;
            break;
          }
        }
      }
      found.forEach(el => el.classList.add("hit"));
      if (found.length) found[0].scrollIntoView({ block: "center", behavior: "smooth" });
      else hint.textContent = "ไม่พบ";
    });
  })();
