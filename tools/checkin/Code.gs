/**
 * ระบบเช็คชื่อ Part-time → Google Sheet + Slack (#avatar-scrum-daily)
 *
 * สคริปต์นี้ต้องผูกกับ Google Sheet (สร้างจาก ส่วนขยาย → Apps Script)
 * Script Property ที่ต้องตั้ง: SLACK_WEBHOOK_URL — Incoming Webhook ของช่อง scrum daily
 */

const TZ = 'Asia/Bangkok';
const SHEET_NAME = 'Log';
const HEADERS = [
  'session_id', 'date', 'check_in', 'check_out', 'hours',
  'yesterday', 'today', 'blockers', 'done', 'edited', 'slack_in', 'slack_out',
];
const COL = HEADERS.reduce((m, h, i) => { m[h] = i + 1; return m; }, {});
const MAX_TEXT = 2000;

// ---------------------------------------------------------------------------
// Web app
// ---------------------------------------------------------------------------

function doGet() {
  return HtmlService.createTemplateFromFile('Index').evaluate()
    .setTitle('เช็คชื่อ Part-time')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/** สถานะปัจจุบันสำหรับหน้า "วันนี้" */
function getState() {
  const sh = getSheet_();
  const rows = readRows_(sh);
  const open = findOpen_(rows);
  const last = rows.length ? rows[rows.length - 1] : null;
  return {
    open: open ? { session_id: open.session_id, check_in: open.check_in.toISOString(), today: String(open.today) } : null,
    suggestYesterday: last && isDate_(last.check_out) ? String(last.done || last.today || '') : '',
    slackConfigured: !!getWebhook_(),
    sheetUrl: sh.getParent().getUrl(),
  };
}

function checkIn(form) {
  return withLock_(() => {
    form = form || {};
    const today = clean_(form.today);
    if (!today) throw new Error('กรุณากรอก "วันนี้จะทำอะไร"');

    const sh = getSheet_();
    const rows = readRows_(sh);
    if (findOpen_(rows)) throw new Error('ยังมีรอบที่ไม่ได้เช็คเอาท์ — เช็คเอาท์ก่อนนะครับ');

    const now = new Date();
    const date = fmt_(now, 'yyyy-MM-dd');
    const n = rows.filter(r => r.date === date).length + 1;
    const id = date + '-' + ('0' + n).slice(-2);
    const yesterday = clean_(form.yesterday);
    const blockers = clean_(form.blockers);

    const rowNum = sh.getLastRow() + 1;
    sh.getRange(rowNum, COL.date).setNumberFormat('@');
    sh.getRange(rowNum, 1, 1, HEADERS.length).setValues([[
      id, date, now, '', '',
      sheetSafe_(yesterday), sheetSafe_(today), sheetSafe_(blockers), '', '', '', '',
    ]]);

    const slack = postSlack_(buildCheckInMessage({
      time: fmt_(now, 'HH:mm'), dateLabel: thaiDateLabel(date), session: n,
      yesterday, today, blockers,
    }));
    sh.getRange(rowNum, COL.slack_in).setValue(slack);
    return { ok: true, session_id: id, slack };
  });
}

/** form.manualTime = "yyyy-MM-ddTHH:mm" (เวลาไทย) เมื่อลืมเช็คเอาท์ */
function checkOut(form) {
  return withLock_(() => {
    form = form || {};
    const sh = getSheet_();
    const rows = readRows_(sh);
    const open = findOpen_(rows);
    if (!open) throw new Error('ยังไม่ได้เช็คอิน');

    const now = new Date();
    let out = now;
    const edited = !!form.manualTime;
    if (edited) {
      out = Utilities.parseDate(String(form.manualTime), TZ, "yyyy-MM-dd'T'HH:mm");
      if (!out || isNaN(out.getTime())) throw new Error('รูปแบบเวลาไม่ถูกต้อง');
    }
    if (out.getTime() <= open.check_in.getTime()) throw new Error('เวลาเลิกงานต้องหลังเวลาเข้างาน');
    if (out.getTime() > now.getTime() + 60000) throw new Error('เวลาเลิกงานต้องไม่อยู่ในอนาคต');

    const minutes = minutesBetween(open.check_in, out);
    const hours = round2(minutes / 60);
    const done = clean_(form.done);

    sh.getRange(open.row, COL.check_out, 1, 2).setValues([[out, hours]]);
    sh.getRange(open.row, COL.done).setValue(sheetSafe_(done));
    sh.getRange(open.row, COL.edited).setValue(edited ? '✓' : '');

    open.hours = hours;
    const weekHours = sumWeekHours(rows, open.date);

    const slack = postSlack_(buildCheckOutMessage({
      time: fmt_(out, 'HH:mm'), inTime: fmt_(open.check_in, 'HH:mm'),
      dateLabel: thaiDateLabel(open.date), minutes, done, edited, weekHours,
    }));
    sh.getRange(open.row, COL.slack_out).setValue(slack);
    return { ok: true, minutes, slack };
  });
}

/** ประวัติทั้งหมด (เก่า → ใหม่) สำหรับหน้า "ประวัติ" */
function getHistory() {
  return readRows_(getSheet_()).map(r => ({
    session_id: String(r.session_id),
    date: r.date,
    check_in: isDate_(r.check_in) ? r.check_in.toISOString() : null,
    check_out: isDate_(r.check_out) ? r.check_out.toISOString() : null,
    hours: typeof r.hours === 'number' ? r.hours : null,
    yesterday: String(r.yesterday), today: String(r.today),
    blockers: String(r.blockers), done: String(r.done),
    edited: r.edited === '✓',
    slack_in: String(r.slack_in), slack_out: String(r.slack_out),
  }));
}

// ---------------------------------------------------------------------------
// รันเองจากหน้า editor
// ---------------------------------------------------------------------------

/** รันครั้งแรกเพื่ออนุญาตสิทธิ์และสร้างแท็บ Log */
function setup() {
  const sh = getSheet_();
  Logger.log('พร้อมใช้งาน: ' + sh.getParent().getUrl());
  Logger.log('Slack webhook: ' + (getWebhook_() ? 'ตั้งค่าแล้ว' : 'ยังไม่ได้ตั้ง SLACK_WEBHOOK_URL'));
}

function testSlack() {
  Logger.log(postSlack_('🧪 ทดสอบระบบเช็คชื่อ — ถ้าเห็นข้อความนี้แปลว่าเชื่อม Slack สำเร็จ'));
}

// ---------------------------------------------------------------------------
// Sheet / Slack helpers
// ---------------------------------------------------------------------------

function getSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('ไม่พบ Google Sheet — สร้างสคริปต์จากเมนู ส่วนขยาย → Apps Script ของ Sheet');
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEADERS);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
    sh.getRange('B:B').setNumberFormat('@');
    sh.getRange('C:D').setNumberFormat('yyyy-mm-dd hh:mm');
    sh.getRange('E:E').setNumberFormat('0.00');
  }
  return sh;
}

function readRows_(sh) {
  const last = sh.getLastRow();
  if (last < 2) return [];
  return sh.getRange(2, 1, last - 1, HEADERS.length).getValues()
    .map((vals, i) => {
      const r = { row: i + 2 };
      HEADERS.forEach((h, j) => { r[h] = vals[j]; });
      r.date = isDate_(r.date) ? fmt_(r.date, 'yyyy-MM-dd') : String(r.date);
      return r;
    })
    .filter(r => r.session_id !== '');
}

function findOpen_(rows) {
  for (let i = rows.length - 1; i >= 0; i--) {
    if (isDate_(rows[i].check_in) && !isDate_(rows[i].check_out)) return rows[i];
  }
  return null;
}

function getWebhook_() {
  return PropertiesService.getScriptProperties().getProperty('SLACK_WEBHOOK_URL');
}

/** คืนค่าสถานะเพื่อบันทึกใน Sheet — ไม่ throw เพื่อให้ข้อมูลเช็คชื่อยังถูกบันทึกแม้ Slack ล่ม */
function postSlack_(text) {
  const url = getWebhook_();
  if (!url) return 'skipped: no webhook';
  try {
    const res = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json',
      payload: JSON.stringify({ text }), muteHttpExceptions: true,
    });
    const code = res.getResponseCode();
    return code === 200 ? 'ok' : 'failed: ' + code + ' ' + res.getContentText().slice(0, 100);
  } catch (e) {
    return 'failed: ' + e.message;
  }
}

function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try { return fn(); } finally { lock.releaseLock(); }
}

function fmt_(d, pattern) { return Utilities.formatDate(d, TZ, pattern); }
function isDate_(v) { return Object.prototype.toString.call(v) === '[object Date]' && !isNaN(v.getTime()); }

// ---------------------------------------------------------------------------
// Pure functions (ทดสอบได้ด้วย Node: tests/logic.test.js)
// ---------------------------------------------------------------------------

function clean_(s) {
  return String(s == null ? '' : s).trim().slice(0, MAX_TEXT);
}

/** กันข้อความที่ขึ้นต้นด้วย = + - @ ถูกตีความเป็นสูตรใน Sheet */
function sheetSafe_(s) {
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function slackEscape(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function round2(n) { return Math.round(n * 100) / 100; }

function minutesBetween(a, b) { return Math.round((b.getTime() - a.getTime()) / 60000); }

function fmtDuration(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return m + ' นาที';
  return m === 0 ? h + ' ชม.' : h + ' ชม. ' + m + ' นาที';
}

/** "2026-09-28" → "2026-09-28" ของวันจันทร์ในสัปดาห์นั้น */
function mondayOf(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() - ((dt.getUTCDay() + 6) % 7));
  return dt.toISOString().slice(0, 10);
}

function sumWeekHours(rows, dateStr) {
  const wk = mondayOf(dateStr);
  return round2(rows
    .filter(r => typeof r.hours === 'number' && mondayOf(r.date) === wk)
    .reduce((s, r) => s + r.hours, 0));
}

function thaiDateLabel(dateStr) {
  const DAYS = ['อาทิตย์', 'จันทร์', 'อังคาร', 'พุธ', 'พฤหัสบดี', 'ศุกร์', 'เสาร์'];
  const MONTHS = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
  const [y, m, d] = dateStr.split('-').map(Number);
  const dow = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return DAYS[dow] + ' ' + d + ' ' + MONTHS[m - 1] + ' ' + y;
}

function buildCheckInMessage(p) {
  const orDash = s => (s ? slackEscape(s) : '–');
  return [
    '🟢 *เช็คอิน ' + p.time + ' น.* · ' + p.dateLabel + (p.session > 1 ? ' (รอบที่ ' + p.session + ')' : ''),
    '*เมื่อวานทำอะไร:* ' + orDash(p.yesterday),
    '*วันนี้จะทำ:* ' + orDash(p.today),
    '*ติดปัญหา:* ' + orDash(p.blockers),
  ].join('\n');
}

function buildCheckOutMessage(p) {
  const lines = [
    '🔴 *เช็คเอาท์ ' + p.time + ' น.* · ' + p.dateLabel + ' · ทำงาน *' + fmtDuration(p.minutes) + '* (' + p.inTime + '–' + p.time + ')',
    '*ทำเสร็จ:* ' + (p.done ? slackEscape(p.done) : '–'),
    '_สัปดาห์นี้รวม ' + fmtDuration(Math.round(p.weekHours * 60)) + '_',
  ];
  if (p.edited) lines.push('✏️ _เวลาเลิกงานถูกใส่ย้อนหลัง (ลืมกดเช็คเอาท์)_');
  return lines.join('\n');
}

if (typeof module !== 'undefined') {
  module.exports = {
    clean_, sheetSafe_, slackEscape, round2, minutesBetween, fmtDuration,
    mondayOf, sumWeekHours, thaiDateLabel, buildCheckInMessage, buildCheckOutMessage,
  };
}
