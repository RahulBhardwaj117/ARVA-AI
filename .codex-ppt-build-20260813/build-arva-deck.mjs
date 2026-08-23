import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const buildDir = "C:\\Users\\Rahul\\.vscode\\Arva AI\\.codex-ppt-build-20260813";
const starterPath = `${buildDir}\\template-starter.pptx`;
const outputPath = "C:\\Users\\Rahul\\.vscode\\Arva AI\\ARVA_AI_Final_Year_Project_Presentation.pptx";
const ogPath = "C:\\Users\\Rahul\\.vscode\\Arva AI\\frontend\\public\\og.png";

const presentation = await PresentationFile.importPptx(await FileBlob.load(starterPath));
const ogBytesBuffer = await fs.readFile(ogPath);
const ogBytes = ogBytesBuffer.buffer.slice(ogBytesBuffer.byteOffset, ogBytesBuffer.byteOffset + ogBytesBuffer.byteLength);

const anchors = {
  "sh/adsz6psr": [0, "FINAL YEAR PROJECT"], "sh/na1gva90": [0, "A\nProject Presentation"],
  "sh/yhcj2twj": [1, "Outline"], "sh/belk7ex8": [1, "Alignment with UN Sustainable"],
  "sh/d8bylsne": [2, "Alignment with UN Sustainable"], "sh/c72hcnmt": [2, "Alignment of Project"], "sh/mxkzih4v": [2, "SDG 9"],
  "sh/wfm9wzap": [3, "Summary"], "sh/ylk7m5sb": [3, "Alignment with UN Sustainable"],
  "sh/u5sr6dwr": [4, "Introduction"], "sh/7218vydg": [4, "Social media platforms"],
  "sh/c7edszq1": [5, "Literature Survey"], "sh/lcne5o7i": [5, "Tan, Y."],
  "sh/oba58fyd": [6, "Literature Survey"], "sh/xg36l4zu": [6, "Kasemrat"],
  "sh/0nu5w3ul": [7, "Research Gap"], "sh/nql4rydw": [7, "Integration Challenge"],
  "sh/by5cnix8": [8, "Project Objectives"], "sh/ovutcnex": [8, "Integration Challenge"],
  "sh/ne5c3idk": [9, "Problem Statement"], "sh/k7yd47ud": [9, "2025 Social Commerce"], "sh/xcnmt47i": [9, "Businesses invest heavily"],
  "sh/254fep0z": [10, "Proposed Work"], "sh/xwfytozm": [10, "2 -3 Slides"],
  "sh/budgrehg": [10, null, 2],
  "sh/bmdozmxg": [11, "Proposed Architecure"], "sh/3ydov2x4": [11, "Fig.1."],
  "sh/snatk3y1": [12, "System Design"], "sh/4jatg3y5": [12, "Fig.1."], "sh/3y1c7yxk": [12, "2-3"],
  "sh/y5o7690r": [13, "Implementation Details"], "sh/a147290v": [13, "Fig.1."], "sh/j6x8ze1c": [13, "3-5"],
  "sh/rq9o3ils": [14, "Result and Analysis"], "sh/qpgnudk7": [14, "Model Performance Evaluation"],
  "sh/kzuxgnel": [15, "Result and Analysis"], "sh/7m5gridc": [15, "Analysis:"], "sh/6d4721of": [15, "Figure 1:"], "sh/m5sf6twn": [15, "Figure 2:"],
  "sh/kr6pwrmd": [16, "Conclusion & Future Work"], "sh/vih8b650": [16, null, 2], "sh/lsfq5wny": [16, "Conclusion"],
  "sh/m1czq9gr": [17, "Conclusion & Future Work"], "sh/5w7it8fa": [17, null, 2], "sh/7250jehc": [17, "Conclusion"],
  "sh/f6dc7atk": [18, "References"], "sh/sj2tcvu9": [18, "P. Yadav"],
  "sh/vep0rqd8": [19, "References"], "sh/8be1gvuh": [19, "Ebrahimi"],
  "sh/kfyp4vid": [20, "Appendix"], "sh/ba5orqhg": [20, "CONTRIBUTION OF PROJECT"],
};

function byId(id) {
  if (id === "tb/cf6l8bi9") return presentation.slides.getItem(3).tables.items[0];
  if (id === "im/zml0zi9o") return presentation.slides.getItem(9).images.items[0];
  if (id === "ch/vm18j2dw") return presentation.slides.getItem(15).charts.items[0];
  if (id === "tb/retwji10") return presentation.slides.getItem(20).tables.items[0];
  const entry = anchors[id];
  if (!entry) throw new Error(`No local anchor for ${id}`);
  const [slideIndex, needle, blankIndex] = entry;
  const shapes = presentation.slides.getItem(slideIndex).shapes.items;
  if (needle === null) {
    const blank = blankIndex === undefined ? shapes.find((shape) => !String(shape.text ?? "").trim()) : shapes[blankIndex];
    if (!blank) throw new Error(`No blank inherited shape for ${id}`);
    return blank;
  }
  const target = shapes.find((shape) => String(shape.text ?? "").includes(needle));
  if (target) return target;
  const headerCandidate = shapes.find((shape) => Number(shape.position?.top) <= 5 && Number(shape.position?.height) >= 70 && String(shape.text ?? "").trim());
  if (headerCandidate) return headerCandidate;
  throw new Error(`No inherited shape matching ${needle} for ${id}`);
}

function write(id, text) {
  byId(id).text = text;
}

function notes(slideIndex, sourceLines) {
  const slide = presentation.slides.getItem(slideIndex);
  slide.speakerNotes.textFrame.setText(`[Sources]\n${sourceLines.join("\n")}`);
  slide.speakerNotes.setVisible(true);
}

function addNode(slide, { name, text, left, top, width, height, fill = "#fff7ed", line = "#b91c1c", fontSize = 16 }) {
  const node = slide.shapes.add({
    geometry: "roundRect",
    name,
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: 1.5 },
    borderRadius: "rounded-xl",
  });
  node.text = text;
  node.text.style = { fontSize, bold: true, color: "#1f2937", alignment: "center", verticalAlignment: "middle" };
  return node;
}

function addLabel(slide, { text, left, top, width, height, fontSize = 17, color = "#1f2937", bold = false }) {
  const label = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  label.text = text;
  label.text.style = { fontSize, bold, color, alignment: "center" };
  return label;
}

function addArrow(slide, from, to, fromSide = "right", toSide = "left") {
  slide.shapes.connect(from, to, {
    kind: "elbow",
    fromSide,
    toSide,
    line: { style: "solid", fill: "#b91c1c", width: 2 },
    head: { type: "triangle", width: "sm", length: "sm" },
  });
}

function styleHeader(id) {
  const header = byId(id);
  header.position = { left: 145, top: 0, width: 1120, height: 95 };
  header.text.style = { fontSize: 34, bold: true, color: "#ffffff", alignment: "center" };
}

// 1 — cover
write("sh/adsz6psr", "FINAL YEAR PROJECT");
write("sh/na1gva90", "A\nProject Presentation on\n\nARVA AI\nAutonomous Decision Intelligence System\n\nPresented By\nProject Team\n\nGuided By\nFaculty Guide\n\nDepartment of Computer Science & Engineering\nITS Engineering College, Greater Noida\nDr. A.P.J. Abdul Kalam Technical University, Lucknow, Uttar Pradesh");
notes(0, ["Internal source: README.md — ARVA AI project scope and positioning."]);

// 2 — outline
write("sh/yhcj2twj", "Outline");
write("sh/belk7ex8", "1. Sustainable Development Alignment\n2. Introduction & Literature Survey\n3. Research Gap & Objectives\n4. Problem Statement\n5. Proposed Work & Methodology\n6. System Architecture & Implementation\n7. Results and Analysis\n8. Conclusion & Future Work\n9. References & Project Contribution");
notes(1, ["Internal source: README.md and docs/architecture.md."]);

// 3 — SDG narrative
write("sh/d8bylsne", "Alignment with UN Sustainable Development Goals (SDGs)");
write("sh/c72hcnmt", "ARVA AI aligns with resilient, innovative and sustainable digital infrastructure.");
write("sh/mxkzih4v", "SDG 9 — Industry, Innovation & Infrastructure\n\nARVA AI advances resilient digital infrastructure by turning telemetry, forecasting and constrained optimization into explainable AI-infrastructure decisions. Its simulation-first digital twin enables safe experimentation before operational rollout.\n\nSDG 8 — Decent Work & Economic Growth\n\nBy reducing manual incident triage and improving use of expensive GPU capacity, the system supports more productive technical operations and responsible growth of AI-enabled work.\n\nSDG 13 — Climate Action\n\nEnergy, power and cost are part of each plan evaluation, making resource-aware scheduling visible and governable.");
notes(2, ["Internal source: README.md; docs/architecture.md; docs/optimization.md.", "External context: United Nations Sustainable Development Goals, https://sdgs.un.org/goals"]);

// 4 — SDG table
write("sh/wfm9wzap", "Summary");
write("sh/ylk7m5sb", "ARVA AI — Sustainable Development Contribution");
const sdgTable = byId("tb/cf6l8bi9");
const sdgRows = [
  ["Focus Area", "SDG Target", "ARVA AI Contribution"],
  ["Innovation", "SDG 9.5 — research & innovation", "Applies forecasting, policy validation and CP-SAT optimization to GPU infrastructure."],
  ["Digital Infrastructure", "SDG 9.1 — resilient infrastructure", "Uses a persistent digital twin to test disruptions, recovery and replanning safely."],
  ["Resource Efficiency", "SDG 8.2 — productivity", "Compares scheduling alternatives using cost, queue, SLA and efficiency outcomes."],
  ["Climate Awareness", "SDG 13.3 — climate action", "Includes power and energy estimates in governed infrastructure decisions."]
];
for (let r = 0; r < sdgRows.length; r += 1) {
  for (let c = 0; c < sdgRows[r].length; c += 1) {
    sdgTable.cells.set(r, c, sdgRows[r][c]);
  }
}
notes(3, ["Internal source: docs/architecture.md; docs/optimization.md.", "External context: United Nations Sustainable Development Goals, https://sdgs.un.org/goals"]);

// 5 — introduction
write("sh/u5sr6dwr", "Introduction");
write("sh/7218vydg", "AI infrastructure teams must decide where workloads run, when to replan and how to recover from failure — often under cost, capacity and policy pressure.\n\nTraditional observability shows utilization and alerts, but leaves the decision to the operator.\n\nARVA AI is a simulation-first autonomous decision-intelligence control plane. It observes a persistent GPU digital twin, forecasts demand, detects operational risk, compares plans, validates policy and records outcomes.\n\nThe central question: not only “What is happening now?” but “What should happen next — and why?”");
notes(4, ["Internal source: README.md — product positioning and included scope."]);

// 6 — literature survey 1
write("sh/c7edszq1", "Literature Survey");
write("sh/lcne5o7i", "Cluster management research shows that resource allocation is more than simple placement.\n\nBorg demonstrated policy-aware cluster management at very large scale, combining admission control, packing, monitoring and simulation tools.\n\nTiresias focused on distributed deep-learning jobs, where uncertain duration, multi-GPU demand and queue delay make general schedulers insufficient.\n\nGavel showed why hardware heterogeneity matters: different models perform differently across accelerator types, so allocation policy must be heterogeneity-aware.\n\nThese works motivate ARVA AI’s combination of workload evidence, constrained placement and alternative-plan evaluation.");
notes(5, ["External sources:", "Verma et al. (2015), Borg — https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/", "Gu et al. (2019), Tiresias — https://www.usenix.org/conference/nsdi19/presentation/gu", "Narayanan et al. (2020), Gavel — https://arxiv.org/abs/2008.09213"]);

// 7 — literature survey 2
write("sh/oba58fyd", "Literature Survey");
write("sh/xg36l4zu", "ARVA AI translates research lessons into an operator-facing decision loop.\n\nA digital twin creates a safe, deterministic environment for forecasting demand, testing failures and evaluating recovery.\n\nInstead of exposing a single opaque scheduling result, ARVA evaluates five heuristics plus an OR-Tools CP-SAT alternative under the same workload state.\n\nEvery candidate plan carries objective values, policy violations, rationale and expected outcome.\n\nThe design joins optimization quality with explainability, governance and replayable evidence.");
notes(6, ["Internal source: docs/architecture.md; docs/optimization.md.", "External source: Google OR-Tools CP-SAT documentation — https://developers.google.com/optimization/cp/"]);

// 8 — research gap
write("sh/0nu5w3ul", "Research Gap");
write("sh/nql4rydw", "Operational gap: Existing infrastructure dashboards reveal utilization and incidents, but do not explain the best next action.\n\nOptimization gap: A scheduler may generate a placement, yet operators need alternatives that expose trade-offs among cost, queue delay, SLA and energy.\n\nGovernance gap: Automated actions need explicit policy checks, approval gates, role-based access and an immutable audit trail.\n\nSafety gap: Connecting experimental AI directly to production clusters creates operational risk.\n\nARVA AI addresses these gaps through a simulation-first, closed-loop control plane that keeps decisions measurable, explainable and governed.");
notes(7, ["Internal source: README.md; docs/architecture.md; docs/optimization.md."]);

// 9 — objectives
write("sh/by5cnix8", "Project Objectives");
write("sh/ovutcnex", "1. Model a persistent, heterogeneous GPU fleet as a deterministic digital twin.\n\n2. Produce demand forecasts and evidence-backed capacity, queue, cost and reliability risks.\n\n3. Compare FIFO, priority, fair-share, bin-packing, deadline-aware and CP-SAT plans on a common state.\n\n4. Enforce policy guardrails across simulation, recommendation, approval and controlled-autonomous modes.\n\n5. Give operators a complete decision trail: alternatives, rationale, actor, execution state and measured outcome.\n\n6. Demonstrate disruption recovery and repeatable scheduler evaluation.");
notes(8, ["Internal source: README.md; docs/architecture.md; docs/optimization.md; docs/demo.md."]);

// 10 — problem statement and ARVA visual
write("sh/ne5c3idk", "Problem Statement");
write("sh/k7yd47ud", "Decision intelligence for AI infrastructure");
write("sh/xcnmt47i", "GPU infrastructure is heterogeneous, shared and disruption-prone. Demand spikes, deadline-sensitive jobs, rising prices and node failures can interact faster than manual workflows.\n\nThe challenge is to recommend a feasible action that balances throughput, urgency, cost, power and safety — while allowing an operator to understand and govern that choice.\n\nARVA AI addresses this challenge in a controlled simulator before real infrastructure adapters are introduced.");
const problemHero = byId("im/zml0zi9o");
problemHero.replace({ blob: ogBytes, contentType: "image/png", alt: "ARVA AI autonomous decision intelligence visual", fit: "cover" });
problemHero.frame = { left: 762, top: 119, width: 495, height: 456 };
problemHero.crop = { left: 0.20, top: 0.05, right: 0.05, bottom: 0.05 };
notes(9, ["Internal source: README.md — simulation-first boundary and product positioning.", "Asset: frontend/public/og.png (project-owned ARVA AI visual)."]);

// 11 — proposed work
write("sh/254fep0z", "Proposed Work");
write("sh/xwfytozm", "ARVA AI converts observed infrastructure state into a governed next-best action.");
write("sh/budgrehg", "Observe → Predict → Assess → Optimize → Validate → Decide → Execute → Learn");
notes(10, ["Internal source: docs/architecture.md — closed decision loop."]);

// 12 — methodology flow
write("sh/bmdozmxg", "Proposed Architecture / Methodology");
write("sh/3ydov2x4", "Fig. 1. ARVA AI closed-loop methodology");
const methodSlide = presentation.slides.getItem(11);
methodSlide.images.items[0].frame = { left: 60, top: 40, width: 0, height: 0 };
const m1 = addNode(methodSlide, { name: "twin", text: "Digital\nTwin", left: 210, top: 305, width: 130, height: 70, fill: "#fff1f2" });
const m2 = addNode(methodSlide, { name: "forecast", text: "Forecast +\nRisk", left: 365, top: 305, width: 130, height: 70, fill: "#fff7ed" });
const m3 = addNode(methodSlide, { name: "optimize", text: "Scheduler\nAlternatives", left: 520, top: 305, width: 145, height: 70, fill: "#fefce8" });
const m4 = addNode(methodSlide, { name: "policy", text: "Policy +\nApproval", left: 690, top: 305, width: 130, height: 70, fill: "#eff6ff" });
const m5 = addNode(methodSlide, { name: "outcome", text: "Outcome +\nReplan", left: 845, top: 305, width: 135, height: 70, fill: "#f0fdf4" });
addArrow(methodSlide, m1, m2); addArrow(methodSlide, m2, m3); addArrow(methodSlide, m3, m4); addArrow(methodSlide, m4, m5);
m1.bringToFront(); m2.bringToFront(); m3.bringToFront(); m4.bringToFront(); m5.bringToFront();
addLabel(methodSlide, { text: "Persistent workload, node and telemetry state", left: 210, top: 245, width: 770, height: 28, fontSize: 18, color: "#7f1d1d", bold: true });
addLabel(methodSlide, { text: "Measured cost • energy • queue • SLA • reliability become evidence for the next planning cycle", left: 210, top: 405, width: 770, height: 40, fontSize: 16 });
notes(11, ["Internal source: docs/architecture.md — closed loop; docs/optimization.md — alternative generation and constraints."]);

// 13 — system architecture
const architectureLegacyBullet = byId("sh/3y1c7yxk");
write("sh/snatk3y1", "System Design");
write("sh/4jatg3y5", "Fig. 2. ARVA AI control-plane architecture");
write("sh/3y1c7yxk", "");
architectureLegacyBullet.position = { left: 60, top: 40, width: 0, height: 0 };
architectureLegacyBullet.text.style = { fontSize: 1, color: "#ffffff" };
const architectureSlide = presentation.slides.getItem(12);
const a1 = addNode(architectureSlide, { name: "browser", text: "Operator\nBrowser", left: 185, top: 290, width: 140, height: 65, fill: "#fff7ed" });
const a2 = addNode(architectureSlide, { name: "frontend", text: "Vinext / React\nControl Plane", left: 365, top: 290, width: 165, height: 65, fill: "#fff1f2" });
const a3 = addNode(architectureSlide, { name: "api", text: "FastAPI\nDecision Services", left: 570, top: 270, width: 180, height: 82, fill: "#fefce8" });
const a4 = addNode(architectureSlide, { name: "redis", text: "Redis\nEvents + Pub/Sub", left: 820, top: 205, width: 170, height: 65, fill: "#eff6ff" });
const a5 = addNode(architectureSlide, { name: "worker", text: "Simulation\nWorker", left: 820, top: 370, width: 170, height: 65, fill: "#f0fdf4" });
const a6 = addNode(architectureSlide, { name: "db", text: "PostgreSQL\nSource of Truth", left: 570, top: 445, width: 180, height: 65, fill: "#fdf2f8" });
addArrow(architectureSlide, a1, a2); addArrow(architectureSlide, a2, a3); addArrow(architectureSlide, a3, a4); addArrow(architectureSlide, a3, a5); addArrow(architectureSlide, a3, a6, "bottom", "top"); addArrow(architectureSlide, a5, a6, "left", "right");
addLabel(architectureSlide, { text: "REST + WebSocket", left: 420, top: 245, width: 110, height: 24, fontSize: 14, color: "#7f1d1d" });
notes(12, ["Internal source: docs/architecture.md — component architecture and responsibilities."]);

// 14 — implementation
const implementationLegacyBullet = byId("sh/j6x8ze1c");
write("sh/y5o7690r", "Implementation Details");
write("sh/a147290v", "Fig. 3. Modular implementation and governed autonomy");
write("sh/j6x8ze1c", "");
implementationLegacyBullet.position = { left: 60, top: 40, width: 0, height: 0 };
implementationLegacyBullet.text.style = { fontSize: 1, color: "#ffffff" };
const implementationSlide = presentation.slides.getItem(13);
const i1 = addNode(implementationSlide, { name: "twin-module", text: "Twin &\nSimulation", left: 195, top: 245, width: 155, height: 75, fill: "#fff1f2" });
const i2 = addNode(implementationSlide, { name: "intel-module", text: "Forecasting &\nRisk Evidence", left: 420, top: 245, width: 175, height: 75, fill: "#fff7ed" });
const i3 = addNode(implementationSlide, { name: "decision-module", text: "Optimization &\nPolicy", left: 665, top: 245, width: 165, height: 75, fill: "#fefce8" });
const i4 = addNode(implementationSlide, { name: "govern-module", text: "Decisions, Audit\n& Experiments", left: 900, top: 245, width: 175, height: 75, fill: "#eff6ff" });
const i5 = addNode(implementationSlide, { name: "modes", text: "Modes: Simulation • Recommendation • Approval • Controlled Autonomous", left: 340, top: 410, width: 610, height: 68, fill: "#f0fdf4", fontSize: 17 });
addArrow(implementationSlide, i1, i2); addArrow(implementationSlide, i2, i3); addArrow(implementationSlide, i3, i4); addArrow(implementationSlide, i3, i5, "bottom", "top");
notes(13, ["Internal source: README.md; docs/architecture.md — modules, audit and deployment modes."]);

// 15 — result summary
write("sh/rq9o3ils", "Result and Analysis");
write("sh/qpgnudk7", "Verification confirms that ARVA AI is a working, deterministic simulation-first MVP.\n\nValidation gates\n• Backend lint and 15 pytest tests passed\n• Frontend lint, test suite, type check and production build passed\n• Docker services, database migrations, authentication, security headers, WebSocket telemetry and durable Redis events passed\n• Seeded environment: 3 clusters, 15 GPU nodes, 3 profiles, 3 teams and 200 workloads\n\nDemonstrated scenario\nA 90-minute baseline was followed by a demand spike, urgent deadline workload, 45% GPU price increase and active-node failure. The system produced forecasts, risks, alternative plans, policy checks and a repeatable recovery sequence.");
notes(14, ["Internal source: docs/final-verification.md — static, runtime and demo verification."]);

// 16 — measured chart
const scoreHeading = byId("sh/7m5gridc");
const scoreLeft = byId("sh/6d4721of");
const scoreRight = byId("sh/m5sf6twn");
write("sh/kzuxgnel", "Result and Analysis");
write("sh/7m5gridc", "Scheduler comparison — same disrupted workload state");
write("sh/6d4721of", "ARVA CP-SAT achieved the highest composite score and the lowest estimated cost among the evaluated alternatives.\n\nRecovery restored 15/15 nodes.\n\nThese are measured demo outputs.");
write("sh/m5sf6twn", "ARVA CP-SAT — 675.455 score • $854.16 • 51 jobs\n\nFIFO — 667.360 score • $885.17 • 51 jobs");
const resultsChart = byId("ch/vm18j2dw");
resultsChart.position = { left: 60, top: 40, width: 0, height: 0 };
presentation.slides.getItem(15).images.items[0].frame = { left: 60, top: 40, width: 0, height: 0 };
presentation.slides.getItem(15).charts.add("bar", {
  position: { left: 62, top: 190, width: 505, height: 235 },
  title: "Composite Scheduler Score",
  titleTextStyle: { fontSize: 17, bold: true, fill: "#7f1d1d" },
  categories: ["FIFO", "Priority", "Fair share", "Bin packing", "Deadline aware", "ARVA CP-SAT"],
  series: [{ name: "Score", values: [667.360, 647.686, 638.463, 637.347, 621.179, 675.455], fill: "#b91c1c" }],
  barOptions: { direction: "bar", grouping: "clustered", gapWidth: 36 },
  hasLegend: false,
  xAxis: { majorGridlines: { style: "solid", fill: "#e5e7eb", width: 1 }, textStyle: { fontSize: 11, fill: "#374151" } },
  yAxis: { textStyle: { fontSize: 11, fill: "#374151" }, line: { style: "solid", fill: "#d1d5db", width: 1 } },
  dataLabels: { showValue: true, position: "outEnd", textStyle: { fontSize: 11, fill: "#7f1d1d", bold: true } }
});
notes(15, ["Internal source: docs/final-verification.md — scheduler scores, estimated cost, job placement and recovery result."]);

// 17 — operator experience
write("sh/kr6pwrmd", "Operator Experience");
write("sh/vih8b650", "A complete decision trail for the AI-infrastructure operator");
write("sh/lsfq5wny", "Command Center: fleet, capacity and governed actions; Simulation: inject demand, price and node-failure events; Forecasting & Risk Center: inspect evidence; Decisions & Experiments: compare, approve and replay; Audit: trace material decisions.");
notes(16, ["Internal source: README.md; docs/demo.md — implemented UI routes and recommended demo journey."]);

// 18 — conclusion
write("sh/m1czq9gr", "Conclusion & Future Work");
write("sh/5w7it8fa", "ARVA AI demonstrates a governed path from infrastructure signals to measurable decisions.");
write("sh/7250jehc", "Conclusion\nARVA AI combines a persistent GPU digital twin, forecasting, risk evidence, scheduler alternatives, CP-SAT placement and policy controls in one explainable loop.\n\nCurrent boundary\nThe project is intentionally simulation-first: it does not yet write to Kubernetes or cloud control planes.\n\nFuture work\nAdd audited infrastructure adapters, TLS and secret rotation, managed PostgreSQL/Redis with backups, richer ML forecasting and production safety reviews.");
notes(17, ["Internal source: README.md — production boundary; docs/final-verification.md — verified outcome."]);

// 19 — project references
write("sh/f6dc7atk", "References");
write("sh/sj2tcvu9", "[1] ARVA AI Project README. Autonomous Decision Intelligence System.\n\n[2] ARVA AI Architecture Documentation. Control-plane shape, closed loop, security boundaries and deployment modes.\n\n[3] ARVA AI Optimization Documentation. Scheduler alternatives, CP-SAT model and policy-aware plan ranking.\n\n[4] ARVA AI Simulation Documentation. Deterministic lifecycle, disruptions, checkpoints and recovery.\n\n[5] ARVA AI Demo Documentation. Official repeatable demand, price and node-failure scenario.\n\n[6] ARVA AI Final Verification. Test/runtime gates and measured scheduler/recovery outcomes.");
notes(18, ["Internal sources: README.md; docs/architecture.md; docs/optimization.md; docs/simulation.md; docs/demo.md; docs/final-verification.md."]);

// 20 — external references
write("sh/vep0rqd8", "References");
write("sh/8be1gvuh", "[7] Verma, A. et al. (2015). Large-scale cluster management at Google with Borg. EuroSys.\nhttps://research.google/pubs/large-scale-cluster-management-at-google-with-borg/\n\n[8] Gu, J. et al. (2019). Tiresias: A GPU Cluster Manager for Distributed Deep Learning. NSDI.\nhttps://www.usenix.org/conference/nsdi19/presentation/gu\n\n[9] Narayanan, D. et al. (2020). Heterogeneity-Aware Cluster Scheduling Policies for Deep Learning Workloads. OSDI.\nhttps://arxiv.org/abs/2008.09213\n\n[10] Google OR-Tools. Constraint Optimization / CP-SAT documentation.\nhttps://developers.google.com/optimization/cp/\n\n[11] United Nations. Sustainable Development Goals.\nhttps://sdgs.un.org/goals");
notes(19, ["External sources listed on slide."]);

// 21 — contribution appendix
write("sh/kfyp4vid", "Appendix");
write("sh/ba5orqhg", "CONTRIBUTION OF PROJECT");
const contribution = byId("tb/retwji10");
const contributionRows = [["1. Objective & Relevance", "A governed decision layer for shared AI/GPU infrastructure."],["2. Technical Novelty", "Digital twin + alternatives + policy + audit in one closed loop."],["3. Expected Outcome", "Explainable, measurable and replayable infrastructure decisions."],["4. Social Relevance", "More productive and safer AI-infrastructure operations."],["5. Environmental Relevance", "Cost, power and energy are evaluated with each plan."],["6. Ethical Consideration", "RBAC, explicit autonomy modes, approvals and append-only audit events."],["7. Production Path", "Audited adapters, TLS, secret rotation and managed data services."]];
for (let r = 0; r < contributionRows.length; r += 1) { contribution.cells.set(r, 0, contributionRows[r][0]); contribution.cells.set(r, 1, contributionRows[r][1]); }
notes(20, ["Internal source: README.md; docs/architecture.md; docs/optimization.md."]);

notes(21, ["Thank-you closing slide based on supplied academic template."]);

// Normalize inherited title frames that did not retain their original color after text replacement.
[
  "sh/yhcj2twj", "sh/d8bylsne", "sh/ylk7m5sb", "sh/u5sr6dwr", "sh/c7edszq1", "sh/oba58fyd",
  "sh/0nu5w3ul", "sh/by5cnix8", "sh/ne5c3idk", "sh/254fep0z", "sh/bmdozmxg", "sh/snatk3y1",
  "sh/y5o7690r", "sh/rq9o3ils", "sh/kzuxgnel", "sh/kr6pwrmd", "sh/m1czq9gr", "sh/f6dc7atk",
  "sh/vep0rqd8", "sh/kfyp4vid"
].forEach(styleHeader);

// Replace three inherited high-density text frames with clean, presentation-scale compositions.
const sdgSlide = presentation.slides.getItem(2);
sdgSlide.shapes.add({ geometry: "rect", position: { left: 0, top: 95, width: 1280, height: 580 }, fill: "#ffffff", line: { style: "solid", fill: "#ffffff", width: 0 } });
sdgSlide.shapes.add({ geometry: "rect", position: { left: 160, top: 95, width: 1120, height: 52 }, fill: "#d40000", line: { style: "solid", fill: "#d40000", width: 0 } });
addLabel(sdgSlide, { text: "ARVA AI aligns with resilient, innovative and sustainable digital infrastructure.", left: 150, top: 120, width: 980, height: 34, fontSize: 18, color: "#7f1d1d", bold: true });
addLabel(sdgSlide, { text: "SDG 9 — Industry, Innovation & Infrastructure", left: 150, top: 210, width: 980, height: 35, fontSize: 24, color: "#1f2937", bold: true });
addLabel(sdgSlide, { text: "ARVA turns telemetry, forecasting and constrained optimization into explainable AI-infrastructure decisions. Its simulation-first digital twin enables safe experimentation before operational rollout.", left: 180, top: 270, width: 920, height: 70, fontSize: 20, color: "#1f2937" });
addLabel(sdgSlide, { text: "SDG 8 & SDG 13", left: 150, top: 400, width: 980, height: 35, fontSize: 24, color: "#1f2937", bold: true });
addLabel(sdgSlide, { text: "Better use of costly GPU capacity supports productive technical work, while cost, power and energy are evaluated with every plan.", left: 180, top: 455, width: 920, height: 55, fontSize: 20, color: "#1f2937" });

const synthesisSlide = presentation.slides.getItem(6);
synthesisSlide.shapes.add({ geometry: "rect", position: { left: 0, top: 95, width: 1280, height: 580 }, fill: "#ffffff", line: { style: "solid", fill: "#ffffff", width: 0 } });
synthesisSlide.shapes.add({ geometry: "rect", position: { left: 160, top: 0, width: 1120, height: 95 }, fill: "#d40000", line: { style: "solid", fill: "#d40000", width: 0 } });
addLabel(synthesisSlide, { text: "Literature Survey", left: 180, top: 20, width: 1080, height: 42, fontSize: 34, color: "#ffffff", bold: true });
addLabel(synthesisSlide, { text: "From cluster research to an operator-facing decision loop", left: 150, top: 150, width: 980, height: 34, fontSize: 20, color: "#7f1d1d", bold: true });
addLabel(synthesisSlide, { text: "Digital twin — a safe deterministic environment for forecasting demand, testing failures and evaluating recovery.", left: 170, top: 250, width: 940, height: 44, fontSize: 20, color: "#1f2937" });
addLabel(synthesisSlide, { text: "Alternative plans — five heuristics plus OR-Tools CP-SAT are evaluated under the same workload state.", left: 170, top: 350, width: 940, height: 44, fontSize: 20, color: "#1f2937" });
addLabel(synthesisSlide, { text: "Governed outcome — every candidate carries objective values, policy checks, rationale and expected impact.", left: 170, top: 450, width: 940, height: 44, fontSize: 20, color: "#1f2937" });

const proposedSlide = presentation.slides.getItem(10);
proposedSlide.shapes.add({ geometry: "rect", position: { left: 0, top: 95, width: 1280, height: 580 }, fill: "#ffffff", line: { style: "solid", fill: "#ffffff", width: 0 } });
addLabel(proposedSlide, { text: "ARVA turns observed infrastructure state into a governed next-best action.", left: 150, top: 165, width: 980, height: 38, fontSize: 20, color: "#7f1d1d", bold: true });
addLabel(proposedSlide, { text: "Observe  →  Predict  →  Assess  →  Optimize", left: 120, top: 275, width: 1040, height: 55, fontSize: 30, color: "#1f2937", bold: true });
addLabel(proposedSlide, { text: "Validate  →  Decide  →  Execute  →  Learn", left: 180, top: 365, width: 920, height: 55, fontSize: 30, color: "#1f2937", bold: true });
addLabel(proposedSlide, { text: "Each decision is supported by forecasts, risk evidence, scheduler alternatives, policy checks and an auditable outcome.", left: 140, top: 500, width: 1000, height: 40, fontSize: 19, color: "#1f2937" });

const operatorLead = byId("sh/vih8b650");
operatorLead.position = { left: 150, top: 135, width: 980, height: 42 };
operatorLead.text.style = { fontSize: 19, bold: true, color: "#7f1d1d", alignment: "center" };
const operatorBody = presentation.slides.getItem(16).shapes.items.find((shape) => String(shape.text ?? "").includes("Command Center"));
operatorBody.position = { left: 150, top: 250, width: 980, height: 220 };
operatorBody.text.style = { fontSize: 18, color: "#1f2937" };

scoreHeading.position = { left: 60, top: 145, width: 510, height: 40 };
scoreHeading.text.style = { fontSize: 18, bold: true, color: "#1f2937", alignment: "center" };
scoreLeft.position = { left: 60, top: 440, width: 550, height: 130 };
scoreLeft.text.style = { fontSize: 17, color: "#1f2937" };
scoreRight.position = { left: 760, top: 250, width: 430, height: 220 };
scoreRight.text.style = { fontSize: 17, color: "#1f2937" };

const conclusionLead = byId("sh/5w7it8fa");
conclusionLead.position = { left: 150, top: 135, width: 980, height: 48 };
conclusionLead.text.style = { fontSize: 20, bold: true, color: "#7f1d1d", alignment: "center" };
const conclusionBody = presentation.slides.getItem(17).shapes.items.find((shape) => String(shape.text ?? "").startsWith("Conclusion\nARVA AI"));
const conclusionSlide = presentation.slides.getItem(17);
conclusionSlide.images.items[0].frame = { left: 60, top: 40, width: 0, height: 0 };
conclusionBody.position = { left: 60, top: 40, width: 0, height: 0 };
for (const inherited of conclusionSlide.shapes.items) {
  const inheritedText = String(inherited.text ?? "");
  if (inheritedText.includes("Conclusion") || inheritedText.includes("Future work") || inheritedText.includes("Limitation") || inheritedText.includes("This project")) {
    inherited.position = { left: 60, top: 40, width: 0, height: 0 };
  }
}
const conclusionCanvas = conclusionSlide.shapes.add({ geometry: "rect", position: { left: 0, top: 0, width: 1280, height: 720 }, fill: "#ffffff", line: { style: "solid", fill: "#ffffff", width: 0 } });
const conclusionBanner = conclusionSlide.shapes.add({ geometry: "rect", position: { left: 160, top: 0, width: 1120, height: 95 }, fill: "#d40000", line: { style: "solid", fill: "#d40000", width: 0 } });
const conclusionFooter = conclusionSlide.shapes.add({ geometry: "rect", position: { left: 0, top: 675, width: 1280, height: 45 }, fill: "#d40000", line: { style: "solid", fill: "#d40000", width: 0 } });
const conclusionTitle = addLabel(conclusionSlide, { text: "Conclusion & Future Work", left: 180, top: 20, width: 1080, height: 44, fontSize: 34, color: "#ffffff", bold: true });
const conclusion1 = addLabel(conclusionSlide, { text: "ARVA combines a persistent GPU digital twin, forecasting, risk evidence, scheduler alternatives, CP-SAT placement and policy controls in one explainable loop.", left: 160, top: 270, width: 960, height: 60, fontSize: 19, color: "#1f2937", bold: true });
const conclusion2 = addLabel(conclusionSlide, { text: "Current boundary: simulation-first MVP; no Kubernetes or cloud write adapter is enabled.", left: 160, top: 380, width: 960, height: 42, fontSize: 18, color: "#7f1d1d", bold: true });
const conclusion3 = addLabel(conclusionSlide, { text: "Future work: audited infrastructure adapters, TLS and secret rotation, managed PostgreSQL/Redis backups, richer ML forecasting and production safety reviews.", left: 160, top: 475, width: 960, height: 62, fontSize: 18, color: "#1f2937" });

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(outputPath);
for (const [index, slide] of presentation.slides.items.entries()) {
  const png = await presentation.export({ slide, format: "png", scale: 1.5 });
  await fs.writeFile(`${buildDir}\\final-slide-${String(index + 1).padStart(2, "0")}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${buildDir}\\final-slide-${String(index + 1).padStart(2, "0")}.layout.json`, await layout.text());
}
const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
await fs.writeFile(`${buildDir}\\final-montage.webp`, new Uint8Array(await montage.arrayBuffer()));
