const test = require('node:test');
const assert = require('node:assert/strict');
const L = require('../Code.gs');

test('fmtDuration', () => {
  assert.equal(L.fmtDuration(0), '0 นาที');
  assert.equal(L.fmtDuration(45), '45 นาที');
  assert.equal(L.fmtDuration(120), '2 ชม.');
  assert.equal(L.fmtDuration(388), '6 ชม. 28 นาที');
});

test('minutesBetween rounds to nearest minute', () => {
  const a = new Date('2026-09-28T02:12:00Z');
  assert.equal(L.minutesBetween(a, new Date('2026-09-28T08:40:29Z')), 388);
});

test('mondayOf uses Monday-start weeks', () => {
  assert.equal(L.mondayOf('2026-09-28'), '2026-09-28'); // จันทร์
  assert.equal(L.mondayOf('2026-10-04'), '2026-09-28'); // อาทิตย์
  assert.equal(L.mondayOf('2026-10-05'), '2026-10-05');
  assert.equal(L.mondayOf('2026-01-01'), '2025-12-29'); // ข้ามปี
});

test('sumWeekHours only counts closed sessions in the same week', () => {
  const rows = [
    { date: '2026-09-27', hours: 5 },   // สัปดาห์ก่อน
    { date: '2026-09-28', hours: 4.5 },
    { date: '2026-09-30', hours: 3.25 },
    { date: '2026-10-01', hours: '' },  // ยังไม่เช็คเอาท์
  ];
  assert.equal(L.sumWeekHours(rows, '2026-10-01'), 7.75);
});

test('thaiDateLabel', () => {
  assert.equal(L.thaiDateLabel('2026-09-28'), 'จันทร์ 28 ก.ย. 2026');
});

test('sheetSafe_ neutralises formulas', () => {
  assert.equal(L.sheetSafe_('=IMPORTXML("x")'), '\'=IMPORTXML("x")');
  assert.equal(L.sheetSafe_('- bullet'), "'- bullet");
  assert.equal(L.sheetSafe_('ปกติ'), 'ปกติ');
});

test('clean_ trims and caps length', () => {
  assert.equal(L.clean_('  hi  '), 'hi');
  assert.equal(L.clean_(null), '');
  assert.equal(L.clean_('x'.repeat(3000)).length, 2000);
});

test('check-in message escapes Slack control chars and fills blanks', () => {
  const msg = L.buildCheckInMessage({
    time: '09:12', dateLabel: 'จันทร์ 28 ก.ย. 2026', session: 1,
    yesterday: 'อ่าน paper <A> & B', today: 'เขียน lit note', blockers: '',
  });
  assert.match(msg, /^🟢 \*เช็คอิน 09:12 น\.\* · จันทร์ 28 ก\.ย\. 2026$/m);
  assert.match(msg, /อ่าน paper &lt;A&gt; &amp; B/);
  assert.match(msg, /\*ติดปัญหา:\* –/);
  assert.doesNotMatch(msg, /รอบที่/);
  assert.match(L.buildCheckInMessage({ time: '18:00', dateLabel: 'x', session: 2, today: 'y' }), /รอบที่ 2/);
});

test('check-out message shows duration, week total and edited flag', () => {
  const base = { time: '15:40', inTime: '09:12', dateLabel: 'จันทร์ 28 ก.ย. 2026', minutes: 388, done: 'lit note 2 เรื่อง', weekHours: 18.08 };
  const msg = L.buildCheckOutMessage(base);
  assert.match(msg, /ทำงาน \*6 ชม\. 28 นาที\* \(09:12–15:40\)/);
  assert.match(msg, /สัปดาห์นี้รวม 18 ชม\. 5 นาที/);
  assert.doesNotMatch(msg, /ย้อนหลัง/);
  assert.match(L.buildCheckOutMessage({ ...base, edited: true }), /ย้อนหลัง/);
});
