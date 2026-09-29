/**
 * Editable, single-slide appendix matching the supplied final Blue Jay deck.
 * Run a copy in an ignored build directory with @oai/artifact-tool available.
 * Required environment: REPO_ROOT, SKILL_DIR, RUNTIME_PYTHON, REFERENCE_PPTX.
 * Optional: OUTPUT_NAME (a new filename for each finalized revision),
 * FONT_REFERENCE_PPTX (an unchanged slide-33 excerpt when unrelated source
 * slides have unresolved font inheritance; the original source remains intact).
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { Presentation, PresentationFile } from '@oai/artifact-tool';

const root = process.env.REPO_ROOT;
const skill = process.env.SKILL_DIR;
const reference = process.env.REFERENCE_PPTX;
const python = process.env.RUNTIME_PYTHON;
for (const value of [root, skill, reference, python]) {
  if (!value || !path.isAbsolute(value)) throw new Error('Required paths must be absolute.');
}
const tmp = path.join(root, 'work/appendix-detector/build');
const output = path.join(root, 'output/presentations/appendix-detector',
  process.env.OUTPUT_NAME || 'Blue_Jay_부록_환각탐지_학습추론.pptx');
await fs.mkdir(tmp, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });
const referenceSha256 = crypto.createHash('sha256').update(await fs.readFile(reference)).digest('hex');
const fontReference = process.env.FONT_REFERENCE_PPTX || reference;
const fontReferenceSha256 = crypto.createHash('sha256').update(await fs.readFile(fontReference)).digest('hex');
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slide = presentation.slides.add();
slide.background.fill = {
  type: 'gradient', gradientKind: 'linear', angleDeg: 35,
  stops: [{ offset: 0, color: '#D8E8FF' }, { offset: 72000, color: '#FFFFFF' }, { offset: 100000, color: '#F8FBFF' }],
};
const C = { ink: '#1E2D3A', gray: '#5C6D7D', blue: '#3182F6', lightBlue: '#EAF2FF',
  teal: '#1BA897', lightTeal: '#E7F6F3', orange: '#DE8540', lightOrange: '#FFF1E5', border: '#D7E0E9' };
const F = 'Noto Sans KR';
let serial = 0;
function box(name, x, y, w, h, fill = '#FFFFFF', border = 'none', radius = 0, shadow = false) {
  return slide.shapes.add({ name: `${++serial}-${name}`, geometry: radius ? 'roundRect' : 'rect',
    position: { left: x, top: y, width: w, height: h }, fill,
    line: { fill: border, width: border === 'none' ? 0 : 1.1, style: 'solid' },
    ...(radius ? { borderRadius: radius } : {}), ...(shadow ? { shadow: 'shadow-md' } : {}) });
}
function text(name, value, x, y, w, h, size = 22, color = C.ink, bold = false, align = 'left') {
  const s = slide.shapes.add({ name: `${++serial}-${name}`, geometry: 'textbox',
    position: { left: x, top: y, width: w, height: h }, fill: 'none', line: { fill: 'none', width: 0 } });
  s.text = value;
  s.text.style = { typeface: F, fontSize: size, color, bold, alignment: align,
    verticalAlignment: 'middle', autoFit: 'none', wrap: 'none',
    insets: { left: 0, right: 0, top: 0, bottom: 0 } };
  return s;
}
function arrow(x, y) {
  slide.shapes.add({ name: `${++serial}-flow-arrow`, geometry: 'rightArrow',
    position: { left: x, top: y, width: 22, height: 18 }, fill: '#8CA8C6', line: { fill: 'none', width: 0 } });
}
function heading(n, label, x) {
  box('step-badge', x + 23, 174, 40, 35, C.blue, 'none', 10);
  text('step-number', n, x + 23, 174, 40, 35, 20, '#FFFFFF', true, 'center');
  text('step-title', label, x + 76, 172, 270, 39, 25, C.ink, true);
}

// Reference slide 33: blue/black brand, gray appendix heading, pale gradient,
// white rounded content panels and Noto Sans KR. All diagram pieces are editable.
text('brand-blue', 'Blue', 29, 14, 92, 46, 34, '#579DD5', true);
text('brand-jay', 'Jay', 119, 14, 80, 46, 34, '#000000', true);
text('appendix-title', '환각 탐지 모델의 학습·추론 구조', 242, 18, 945, 42, 29, C.gray, true);
text('key-message', '질문과 근거는 함께 읽고, 답변의 각 토큰만 판정', 40, 88, 1180, 42, 30, C.ink, true);

for (const x of [40, 450, 860]) box('main-card', x, 152, 380, 300, '#FFFFFF', C.border, 18, true);
heading('01', '입력 구성', 40);
heading('02', '답변 토큰 학습', 450);
heading('03', '의심 구절 표시', 860);
arrow(425, 294); arrow(835, 294);

// The illustrative text is not a real procurement condition or model output.
const rows = [
  ['질문', '참가 가능한 업체 수는?', 227, C.blue, C.lightBlue],
  ['근거', '4개사 이하', 271, C.teal, C.lightTeal],
  ['답변', '5개사까지 가능합니다.', 315, C.orange, C.lightOrange],
];
for (const [label, value, y, color, fill] of rows) {
  box('example-row', 62, y, 336, 37, fill, 'none', 7);
  text('example-label', label, 74, y, 47, 37, 18, color, true);
  text('example-value', value, 129, y, 258, 37, 20, C.ink);
}
text('input-serialization', '[CLS] 질문·근거 [SEP] 답변 [SEP]', 62, 372, 336, 29, 16.5, C.gray, false, 'center');
text('example-disclaimer', '설명용 입력 예시', 62, 414, 336, 24, 16, C.gray, false, 'center');

box('masked-context', 473, 227, 334, 68, '#F0F4F8', 'none', 9);
text('mask-context-label', '질문·근거·특수 토큰 → −100', 486, 235, 309, 28, 19, C.gray, true, 'center');
text('mask-context-explanation', '문맥으로 읽되, 손실 계산에서 제외', 486, 264, 309, 25, 17, C.gray, false, 'center');
text('answer-only', '답변 토큰에만 정답 라벨 적용', 473, 310, 334, 31, 21, C.ink, true, 'center');
box('supported-label', 473, 352, 155, 53, C.lightTeal, 'none', 10);
box('hallucinated-label', 640, 352, 167, 53, C.lightOrange, 'none', 10);
text('supported', '0 · SUPPORTED', 479, 352, 143, 53, 16, C.teal, true, 'center');
text('hallucinated', '1 · HALLUCINATED', 644, 352, 159, 53, 15.5, C.orange, true, 'center');
text('binary-classification', '지지 / 환각의 이진 분류', 473, 417, 334, 24, 16, C.gray, false, 'center');

text('span-processing', '토큰 점수 → 임계값 → 문자 위치', 883, 229, 334, 32, 19, C.ink, true, 'center');
box('answer-example', 883, 277, 334, 66, '#F5F8FC', 'none', 10);
box('example-highlight', 905, 293, 69, 31, '#FFE96B', 'none', 3);
const answerExample = text('highlighted-answer', '', 908, 290, 297, 37, 24, C.ink);
answerExample.text.set([[{ run: '5개사', textStyle: { bold: true } }, { run: '까지 가능합니다.' }]]);
text('span-merge', '인접한 의심 토큰을 구절로 연결', 883, 361, 334, 32, 20, C.ink, false, 'center');
text('timing', '답변 생성 완료 후 탐지', 883, 401, 334, 27, 18, C.blue, true, 'center');

// Window diagram: overlapping prompt windows, the same answer in each window.
box('window-card', 40, 482, 1200, 179, '#FFFFFF', C.border, 18, true);
text('long-context-title', '긴 문맥은 겹쳐 나눠 검사', 63, 493, 900, 36, 24, C.ink, true);
const barX = 168, unit = 55, gap = 5;
for (let row = 0; row < 3; row++) {
  const y = 538 + row * 34;
  text(`window-${row + 1}`, `창 ${row + 1}`, 108, y + 1, 46, 24, 17, C.gray);
  for (let col = 0; col < 5; col++) {
    const active = col >= row && col < row + 3;
    box('context-token-group', barX + col * (unit + gap), y, unit, 25,
      active ? ['#86B6FC', '#5396F7', '#2978E8'][row] : '#EDF2F7', 'none', 4);
  }
  text('plus-symbol', '+', 474, y, 27, 25, 20, C.gray, false, 'center');
  box('repeated-answer', 506, y, 99, 25, C.lightTeal, 'none', 5);
  text('same-answer', '동일 답변', 510, y, 91, 25, 16, C.teal, true, 'center');
}
box('window-divider', 670, 535, 1.2, 104, C.border);
text('window-process-1', '문맥 창별로 답변 토큰 점수를 계산', 704, 538, 499, 30, 21, C.ink, true);
text('window-process-2', '점수 통합 후 정본 답변의 위치로 복원', 704, 574, 499, 30, 20, C.gray);
text('window-process-3', '처리 한도 초과 구간은 ‘미검사’로 구분', 704, 610, 499, 28, 19, C.orange, true);

text('footer', '구절 표시는 설명용 예시 · 탐지 점수는 정답의 보증이 아님', 40, 680, 1200, 24, 16, C.gray, false, 'right');

slide.speakerNotes.textFrame.setText([
  'Blue Jay — 기술 부록. 모든 도형과 텍스트는 편집 가능.',
  '스타일 참조: 사용자 최종리허설_LastDanceV2!.pptx, 부록 슬라이드 33. 원본 파일은 변경하지 않음.',
  `참조 파일 SHA-256: ${referenceSha256}`,
  '구현 근거(로컬 저장소): src/dataset.py::encode_example, align_labels; demo/detector.py::token_probs, _aggregate, spans; demo-ui/spatial-poc/detector_bridge.py::_worker.',
  '학습: 질문과 근거를 prompt로 만들고 특수 토큰으로 답변을 구분한다. 질문·근거·특수 토큰은 attention 대상이며 label=-100으로 손실에서만 제외한다. 답변 영역에는 SUPPORTED=0/HALLUCINATED=1 라벨을 부여한다.',
  '최대 길이: 학습 인코더는 답변 공간을 먼저 확보하고 prompt 꼬리를 줄인다. 답변 자체가 최대 길이를 넘으면 답변도 잘릴 수 있다. 모든 길이의 답변이 온전히 보장된다는 뜻이 아니다.',
  '추론: 답변 토큰의 HALLUCINATED softmax 점수를 설정된 임계값과 비교한 뒤 원래 답변의 Unicode 문자 offset [start,end)로 복원하고 인접 의심 토큰을 합친다. 이 점수는 답변의 사실성 확률 또는 입찰 적격성 보증이 아니다.',
  '긴 입력: demo/detector.py는 질문과 근거를 합친 prompt에 겹치는 창을 적용하고 각 창에 동일한 답변을 붙인다. 각 창에 질문 전문이 항상 반복되는 것은 아니다. 창별 점수 통합은 설정에 따라 min, min2 또는 mean이며 현재 코드의 기본값은 min이다.',
  '서버 어댑터는 긴 답변을 별도 세그먼트로 처리하고 전체 원문 좌표로 되돌린다. 작업 한도에 걸리면 checked_ranges/unchecked_ranges로 구분한다. 완료 후 탐지이며 스트리밍 중 실시간 토큰 판정을 주장하지 않는다.',
  '4개사/5개사 및 노란 형광펜은 설명용 합성 예시다. 실제 공고 조건, 모델 실측 결과 또는 성능 지표가 아니다. 예시의 단어 상자는 실제 subword 토큰 경계를 표시하지 않는다.',
].join('\n\n'));

const candidatePath = path.join(tmp, 'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const result = await finalizePresentation({
  workspaceDir: root, candidatePath, finalPath: output,
  explicitTotalSlideCount: 1,
  pythonExecutable: python,
  integrityValidatorPath: path.join(skill, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(skill, 'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit'],
  requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: 'reference', families: [F], referencePath: fontReference, referenceSha256: fontReferenceSha256 },
  verifyArtifactToolImport: true,
  receiptPath: path.join(tmp, path.basename(output) + '.validation.json'),
});
await fs.writeFile(path.join(tmp, 'build-metadata.json'), JSON.stringify({ output, referenceSha256, fontReferenceSha256, result }, null, 2));
console.log(JSON.stringify({ output, finalized: true }));
