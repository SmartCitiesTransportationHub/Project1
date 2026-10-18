const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.defineLayout({ name: "W", width: 13.333, height: 7.5 });
pres.layout = "W";
pres.theme = { headFontFace: "Cambria", bodyFontFace: "Calibri" };
pres.defineSlideMaster({ title:"LIGHT", background:{ color:"FFFFFF" }, objects:[
  { text:{ text:"巴塞罗那充电网络 · 网络层 OCPP 攻防仿真（方法论 · 建模 · 协议）", options:{ x:0.5,y:7.08,w:10,h:0.3,fontSize:9,color:"9AA7B5",fontFace:"Calibri",isTextBox:true,margin:0 } } },
]});
pres.defineSlideMaster({ title:"DARK", background:{ color:"0F3D57" } });

const FIG="/home/user/Project1/figs/";
const INK="1A2633", NAVY="0F3D57", TEAL="1AA3C4", RED="E8384F", GREEN="1EA97C", PURPLE="8B4DDB", ORANGE="F08A24", MUT="5D6B7A", CARD="F4F7FB", CARDE="D7E0EA";
function title(s,t){ s.addText(t,{x:0.6,y:0.36,w:12.1,h:0.8,fontSize:28,bold:true,color:NAVY,fontFace:"Cambria",align:"left",valign:"middle",isTextBox:true,margin:0}); }
function kicker(s,t,c){ s.addText(t,{x:0.62,y:0.16,w:12,h:0.3,fontSize:12,bold:true,color:c||TEAL,fontFace:"Calibri",charSpacing:2,isTextBox:true,margin:0}); }
function card(s,x,y,w,h,fill,edge){ s.addShape(pres.ShapeType.roundRect,{x,y,w,h,rectRadius:0.09,fill:{color:fill||CARD},line:{color:edge||CARDE,width:1},shadow:{type:"outer",color:"B9C6D4",opacity:0.3,blur:6,offset:2,angle:90}}); }
function img(s,p,x,y,w,ratio){ s.addImage({path:FIG+p,x,y,w,h:w/ratio}); }
function pill(s,x,y,w,t,col){ s.addShape(pres.ShapeType.roundRect,{x,y,w,h:0.5,rectRadius:0.22,fill:{color:col}}); s.addText(t,{x,y,w,h:0.5,fontSize:11.5,bold:true,color:"FFFFFF",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0}); }
function body(s,items,x,y,w,h,fs){ s.addText(items,{x,y,w,h,fontSize:fs||14,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,paraSpaceAfter:9}); }

// ===== S1 cover (dark) =====
let s=pres.addSlide({masterName:"DARK"});
s.addShape(pres.ShapeType.roundRect,{x:0.9,y:1.0,w:3.4,h:0.5,rectRadius:0.25,fill:{color:"13506F"},line:{color:"2E86AD",width:1}});
s.addText("方法论 · 建模 · OCPP 协议 · 攻防实测",{x:0.9,y:1.0,w:3.4,h:0.5,fontSize:10.5,bold:true,color:"8FE3F5",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText("充电桩会被黑客“远程操纵”吗？",{x:0.9,y:1.75,w:11.5,h:1.4,fontSize:44,bold:true,color:"FFFFFF",fontFace:"Cambria",align:"left",isTextBox:true,margin:0});
s.addText("城市级充电网络“网络层”OCPP 攻防仿真——方法、建模与协议",{x:0.92,y:3.25,w:11.5,h:0.7,fontSize:19,color:"CFE3EF",fontFace:"Calibri",align:"left",isTextBox:true,margin:0});
s.addText("以巴塞罗那大都会区真实数据为底座  ·  全程隔离仿真，不接触任何真实系统",{x:0.92,y:4.0,w:11.5,h:0.5,fontSize:13,color:"8CA9BC",fontFace:"Calibri",align:"left",isTextBox:true,margin:0});
[["37+","家运营商"],["621","个充电点"],["39","个独立后台(CSMS)"],["真实 OCPP 1.6","消息级仿真"]].forEach((c,i)=>{const x=0.9+i*3.0;
  s.addShape(pres.ShapeType.roundRect,{x,y:5.35,w:2.75,h:1.3,rectRadius:0.1,fill:{color:"12405B"},line:{color:"24617E",width:1}});
  s.addText(c[0],{x,y:5.5,w:2.75,h:0.65,fontSize:(c[0].length>4?18:30),bold:true,color:"5AD0E8",align:"center",valign:"middle",fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x,y:6.15,w:2.75,h:0.35,fontSize:11.5,color:"B9D3E0",align:"center",fontFace:"Calibri",isTextBox:true,margin:0});});
s.addNotes("开场：研究充电桩会不会被黑客通过网络层(OCPP)远程操纵。本次重点讲方法论、建模和协议。");

// ===== S2 overview framework =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"研究总览");
img(s,"figLOGIC_framework.png",1.17,0.72,11.0,1.714);
s.addNotes("一页看懂全文逻辑，后面逐块展开方法论/协议/建模。");

// ===== S3 methodology 1: object + metric =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"方法论 ①",TEAL); title(s,"只盯“网络层”，电网只作参照");
body(s,[
  {text:"研究对象：充电桩 ↔ 运营商后台(CSMS) 之间的 OCPP 控制通道（网络层）。",options:{bullet:true,breakLine:true,paraSpaceAfter:12}},
  {text:"不研究电网潮流/频率稳定——电网只作“结果参照”：全城 63.47 MW 仅占电网峰值 0.16%，远低于会出事的 9–11%。",options:{bullet:true,breakLine:true,paraSpaceAfter:12}},
  {text:"为什么盯网络层：攻击者在 OCPP 通道上的行为，能直接映射成可度量的结果。",options:{bullet:true,breakLine:true}},
],0.7,1.7,6.0,3.6,15);
s.addShape(pres.ShapeType.roundRect,{x:0.7,y:5.5,w:6.0,h:1.2,rectRadius:0.08,fill:{color:"EAF6F0"},line:{color:"A8D9C2",width:1}});
s.addText("损失 = 检测时延 τ_d 沿攻击功率曲线的积分（被发现前已造成的）。",{x:0.9,y:5.5,w:5.6,h:1.2,fontSize:13.5,bold:true,color:"1C7A57",align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText("主评价指标：“被发现前造成的损失”",{x:7.0,y:1.55,w:5.7,h:0.4,fontSize:14,bold:true,color:NAVY,fontFace:"Calibri",isTextBox:true,margin:0});
[["受控电量 ΔE","被限功率/停充而少充的电（度 / kWh）",RED],["被拒会话数","因攻击无法开始或被中止的充电次数",ORANGE],["受影响市镇数","含≥1 个被控站点的市镇数",PURPLE]].forEach((c,i)=>{const y=2.05+i*1.55;
  card(s,7.0,y,5.7,1.35,CARD); s.addShape(pres.ShapeType.roundRect,{x:7.0,y,w:0.14,h:1.35,rectRadius:0.0,fill:{color:c[2]}});
  s.addText(c[0],{x:7.3,y:y+0.14,w:5.3,h:0.5,fontSize:16,bold:true,color:c[2],fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x:7.3,y:y+0.66,w:5.3,h:0.6,fontSize:12.5,color:INK,fontFace:"Calibri",isTextBox:true,margin:0});});
s.addNotes("方法论1：研究对象=OCPP控制通道(网络层)；电网只作参照(0.16%)；主指标=被发现前损失(ΔE/被拒会话/受影响市镇)。");

// ===== S4 methodology 2: macro/micro bridge =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"方法论 ②",TEAL); title(s,"一家真实标定，按容量迁移到全城");
img(s,"figC0_bridge.png",1.42,1.35,10.5,2.073);
s.addShape(pres.ShapeType.roundRect,{x:0.9,y:6.3,w:11.5,h:0.85,rectRadius:0.08,fill:{color:"EEF6FB"},line:{color:"BFE0EE",width:1}});
s.addText([{text:"“规模×节律”分解一物两用：",options:{bold:true,color:NAVY,fontSize:13.5}},{text:"① 给没有真实数据的站点生成背景流量；② 同一分解转作后台侧的“物理一致性检测器”。",options:{color:INK,fontSize:13.5}}],{x:1.1,y:6.3,w:11.1,h:0.85,align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("方法论2：宏观(全城多家)↔微观(AMB一家真实)两层；以一家真实标定单后台动力学，按登记容量迁移全城。规模×节律一物两用。");

// ===== S5 protocol 1: OCPP versions & security =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"协议 ①",ORANGE); title(s,"OCPP 协议：版本决定攻防门槛");
[["OCPP 1.6","传输加密可选、设备认证弱；报文可篡改、缺计量完整性。","FDECEC",RED],
 ["OCPP 2.0.1","强制 TLS、证书认证、结构化安全配置档。","EAF6F0",GREEN],
 ["OCPP 2.1 / IEC 63584","Plug&Charge 支付鉴权、面向 V2X/DER 双向。","EEF0FB",PURPLE]].forEach((c,i)=>{const x=0.7+i*4.05;
  card(s,x,1.5,3.8,1.45,c[2]); s.addText(c[0],{x:x+0.2,y:1.62,w:3.5,h:0.5,fontSize:15.5,bold:true,color:c[3],fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x:x+0.2,y:2.12,w:3.45,h:0.75,fontSize:12,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,margin:0});});
img(s,"fig13_reach.png",2.82,3.05,7.7,2.262);
s.addText("读图：加密只压制中间人(A1)与克隆(A2)；后台沦陷(A3)与 DoS(A4) 不随版本消失。（巴塞罗那现网版本未查得出处，按情景假设处理）",{x:0.7,y:6.62,w:12,h:0.33,fontSize:11,italic:true,color:MUT,align:"center",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("协议1：三代OCPP安全差异。版本可行性门控：TLS阻断A1、P&C缩小A2；A3/A4与版本无关。巴塞现网版本仅情景假设。");

// ===== S6 protocol 2: real messages + mapping =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"协议 ②",ORANGE); title(s,"真实 OCPP 报文：正常 vs 攻击映射");
img(s,"fig_ocpp_seq.png",0.55,1.4,8.3,1.550);
body(s,[
  {text:"正常充电 = 一串真实 OCPP 报文：BootNotification / Authorize / StartTransaction / MeterValues / StopTransaction / Heartbeat。",options:{bullet:true,breakLine:true,paraSpaceAfter:12}},
  {text:"攻击不发明新报文——复用同一批，只改：来源(后台沦陷) / 内容(篡改电表) / 节律(DoS 洪泛)。",options:{bullet:true,breakLine:true,paraSpaceAfter:12}},
  {text:"仿真里这些报文被真实收发，不是抽象的“受控比例”。",options:{bullet:true,bold:true,color:ORANGE,breakLine:true}},
],9.05,1.8,3.7,4.4,13.5);
s.addNotes("协议2：真实报文序列图。攻击复用同一批OCPP报文(改来源/内容/节律)，仿真里真实收发，不是抽象模型。");

// ===== S7 modeling 1: architecture =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"建模 ①",PURPLE); title(s,"仿真系统：621 个真实客户端 → 39 个后台");
img(s,"fig_sim_arch.png",0.5,1.45,8.3,1.636);
body(s,[
  {text:"每个充电点 = 一个 Python ocpp 异步客户端，经真实 WebSocket 连到其运营商后台。",options:{bullet:true,breakLine:true,paraSpaceAfter:11}},
  {text:"39 个后台相互独立（控制平面碎片化）。",options:{bullet:true,breakLine:true,paraSpaceAfter:11}},
  {text:"离散虚拟时钟 1 分钟/步、与墙钟解耦——消息处理延迟不污染仿真时间。",options:{bullet:true,breakLine:true,paraSpaceAfter:11}},
  {text:"检测与隔离按后台独立运行。",options:{bullet:true,breakLine:true}},
],9.0,1.75,3.75,4.5,13.5);
s.addNotes("建模1：621真实ocpp客户端→39独立CSMS后台；离散虚拟时钟；真实websocket；按后台独立检测隔离。");

// ===== S8 modeling 2: demand/traffic =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"建模 ②",PURPLE); title(s,"流量建模：真实会话 + 容量定标合成");
card(s,0.7,1.7,5.9,4.2,"EEF6FB"); pill(s,0.95,1.95,3.0,"真实会话回放（AMB 71 站）",TEAL);
body(s,[
  {text:"2025 全年真实充电记录。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"每条会话 → 一串真实 OCPP 报文。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"原始只有起止时刻与总电量；会话内功率按时长均摊重建，该假设单列敏感性分析。",options:{bullet:true,breakLine:true}},
],0.95,2.65,5.4,3.1,14);
card(s,6.75,1.7,5.9,4.2,"F1EEFB"); pill(s,7.0,1.95,3.3,"规模×节律合成（550 站）",PURPLE);
body(s,[
  {text:"无真实数据的站点：功率 scale = DGT 登记额定。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"节律 ρ(t) = AMB 实测的同类功能区利用率。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"每家后台总量 = 其 DGT 登记 MW（真实）。",options:{bullet:true,breakLine:true}},
],7.0,2.65,5.4,3.1,14);
s.addShape(pres.ShapeType.roundRect,{x:0.7,y:6.1,w:11.95,h:0.82,rectRadius:0.08,fill:{color:"FFF4E6"},line:{color:"F0C488",width:1}});
s.addText("合成流量仅作容量定标的“可信占位”，其不确定性随攻防指标一并报告——这正是采用“一家标定、全城迁移”的根本原因。",{x:0.9,y:6.1,w:11.6,h:0.82,fontSize:13,bold:true,color:"B5701A",align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("建模2：AMB 71站真实会话回放(功率重建单列敏感性)；其余550站规模×节律合成(scale=登记额定，节律=实测同区利用率)。合成仅作占位。");

// ===== S9 modeling 3: attack/detect/contain =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"建模 ③",PURPLE); title(s,"攻击 / 检测 / 遏制模型");
const steps=[["①  攻击注入",RED,"被攻破后台按站点繁忙度扇出指令。\n速率：快速 30 / 隐蔽 3 指令/分。"],
 ["②  检测（双信号）",ORANGE,"指令速率 ≥5 条/2min；或\n规模×节律一致性比出带（观测/预期 <0.5 或 >1.5）持续 2min。"],
 ["③  遏制",GREEN,"指令限速 + 告警后 1 分钟按后台隔离并恢复本地充电。"]];
steps.forEach((st,i)=>{const y=1.65+i*1.55; card(s,0.7,y,6.0,1.4,CARD);
  s.addShape(pres.ShapeType.roundRect,{x:0.7,y,w:0.14,h:1.4,fill:{color:st[1]}});
  s.addText(st[0],{x:0.95,y:y+0.12,w:5.6,h:0.45,fontSize:15,bold:true,color:st[1],fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(st[2],{x:0.95,y:y+0.55,w:5.55,h:0.8,fontSize:12.5,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,margin:0});
  if(i<2) s.addShape(pres.ShapeType.line,{x:3.7,y:y+1.4,w:0,h:0.15,line:{color:MUT,width:1.5,endArrowType:"triangle"}});});
img(s,"fig6_detector.png",7.0,2.0,5.6,1.605);
s.addText("一致性检测器：把真实大停电（全网同步跌至期望 0.53）与单站伪造电表区分开——不误报。",{x:7.0,y:5.75,w:5.6,h:0.9,fontSize:12.5,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,margin:0});
s.addNotes("建模3：攻击扇出(30/3指令每分)→双信号检测(指令速率+规模×节律一致性)→限速+1分钟隔离恢复。检测器能区分真停电vs单站造假。");

// ===== S9b algorithm contribution: optimal stopping =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"算法贡献",RED); title(s,"把“何时隔离”求解为最优问题（最优停止）");
body(s,[
  {text:"问题：隔离太晚 → 损失累积；误隔离健康后台 → 中断合法充电。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"建成贝叶斯快速变点检测：良性 r~N(1,σ₀)、攻击 r~N(1−δ,σ₀)，σ₀=0.39 取自真实数据。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"最优规则 = 对后验 pₜ=P(已被攻击) 的阈值 A*（Shiryaev）；A* 最小化 期望损失 c·时延 + K·误隔离。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"六法对比：最优策略严格优于 CUSUM、学习型 ML（孤立森林/单类SVM）与固定规则。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"发现：真实噪声下固定规则误隔离 76%；最优策略降期望损失 84%，越隐蔽、误隔离代价越高优势越大。",options:{bullet:true,bold:true,color:RED,breakLine:true}},
],0.7,1.6,6.05,3.8,13);
img(s,"fig_optstop_oc.png",7.0,1.6,5.95,1.571);
const OS=[["−84%","期望损失↓（δ=0.5）",GREEN],["76%→1.4%","误隔离率",RED],["A*≈0.93","最优隔离阈值",NAVY]];
OS.forEach((c,i)=>{const x=0.75+i*4.1; card(s,x,5.7,3.75,1.1,CARD);
  s.addText(c[0],{x,y:5.78,w:3.75,h:0.6,fontSize:23,bold:true,color:c[2],align:"center",fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x,y:6.36,w:3.75,h:0.35,fontSize:12,color:MUT,align:"center",fontFace:"Calibri",isTextBox:true,margin:0});});
s.addNotes("算法贡献:把'何时隔离'建成贝叶斯快速变点检测/最优停止,求出最优阈值A*。固定规则真实噪声下误隔离76%;最优策略降期望损失84%。这就是'用算法解决问题',不只是分析。");

// ===== S10 experiment design matrix =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"实验设计",TEAL); title(s,"场景矩阵与评价口径");
const hdr={fill:NAVY,color:"FFFFFF",bold:true,fontSize:14,valign:"middle",fontFace:"Calibri"};
const kcell=(t)=>({text:t,options:{fill:"EAF1F8",color:NAVY,bold:true,fontSize:13.5,valign:"middle",align:"left",margin:[4,8,4,8],fontFace:"Calibri"}});
const vcell=(t)=>({text:t,options:{color:INK,fontSize:13,valign:"middle",align:"left",margin:[4,8,4,8],fontFace:"Calibri"}});
const rows=[
 [{text:"维度",options:hdr},{text:"取值 / 说明",options:hdr}],
 [kcell("攻击位置 A"),vcell("A1 链路中间人 · A2 克隆 RFID · A3 后台沦陷(限功率/停充) · A4 后台 DoS")],
 [kcell("协议版本 V"),vcell("OCPP 1.6 · 2.0.1 · 2.1（版本可行性门控：TLS 下 A1 不可行）")],
 [kcell("防御 D"),vcell("D0 无 · D2 指令限速 · D3 按后台隔离 · D5 规模×节律一致性检测（可组合）")],
 [kcell("受控范围"),vcell("单后台（逐家）· 协同前 k 家（k=1…8）· 全城")],
 [kcell("主指标"),vcell("被发现前损失（ΔE、被拒会话、受影响市镇）· 检测时延 τ_d · 误报率")],
 [kcell("可复现"),vcell("固定随机种子 · 每格 3 次重复取中位数 · 真实异常做“假阳性闸门”")],
];
s.addTable(rows,{x:0.7,y:1.6,w:11.95,colW:[2.5,9.45],border:{type:"solid",color:"DDE5EE",pt:1},rowH:0.72,valign:"middle"});
s.addNotes("实验设计：四维场景矩阵(攻击位置×协议版本×防御×范围)；主指标=被发现前损失+τ_d+误报率；可复现(固定种子、3次中位数、真实异常做闸门)。");

// ===== S11 results =====
s=pres.addSlide({masterName:"LIGHT"}); kicker(s,"结果精选（真实仿真实测）",GREEN); title(s,"关键数字");
img(s,"figC4_campaign.png",0.6,1.6,7.9,1.817);
const R=[["2.6–12.3 MW","单后台沦陷可控（最大一家=全城 17%）",RED],
 ["< 10 kWh","检测+隔离后被发现前损失（单后台，>99%）",GREEN],
 ["26.5 kWh","协同攻破前 5 家(44.9 MW)隔离后",TEAL],
 ["0.16%","全城完全受控 占电网峰值",NAVY]];
R.forEach((c,i)=>{const y=1.7+i*1.3; card(s,8.75,y,3.95,1.15,CARD);
  s.addText(c[0],{x:8.9,y:y+0.12,w:3.7,h:0.55,fontSize:24,bold:true,color:c[2],fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x:8.9,y:y+0.66,w:3.7,h:0.42,fontSize:11.5,color:MUT,fontFace:"Calibri",align:"left",isTextBox:true,margin:0});});
s.addNotes("结果：单后台2.6-12.3MW→隔离后<10kWh(>99%)；协同5家11889→26.5kWh；电网0.16%。图是协同campaign累积曲线(红升绿平)。");

// ===== S12 conclusion (dark) =====
s=pres.addSlide({masterName:"DARK"});
s.addText("结论与价值",{x:0.7,y:0.5,w:12,h:0.7,fontSize:30,bold:true,color:"FFFFFF",fontFace:"Cambria",isTextBox:true,margin:0});
[["方法可核查","把抽象的“控制电网 x%”拆成网络层问题：攻破几家后台、可达多少 MW、被发现前损失多少度。",TEAL],
 ["建模够真","621 个真实 OCPP 客户端 + 真实报文 + 离散虚拟时钟；一家真实标定、全城迁移，物理自洽。",GREEN],
 ["协议是关键","攻防门槛由 OCPP 版本决定：加密压制中间人/克隆，但后台沦陷与 DoS 须靠隔离与检测。",ORANGE],
 ["现实指导","真正该防的是网络层后台通道而非电网；碎片化是安全资产，别盲目追求统一大平台。",PURPLE]].forEach((v,i)=>{const col=i%2,row=Math.floor(i/2);const x=0.7+col*6.1,y=1.5+row*1.95;
  s.addShape(pres.ShapeType.roundRect,{x,y,w:5.85,h:1.75,rectRadius:0.09,fill:{color:"12405B"},line:{color:"24617E",width:1}});
  s.addShape(pres.ShapeType.roundRect,{x:x+0.2,y:y+0.22,w:1.75,h:0.45,rectRadius:0.22,fill:{color:v[2]}});
  s.addText(v[0],{x:x+0.2,y:y+0.22,w:1.75,h:0.45,fontSize:12.5,bold:true,color:"0F3D57",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
  s.addText(v[1],{x:x+0.2,y:y+0.74,w:5.45,h:0.95,fontSize:12.5,color:"DCEAF2",align:"left",valign:"top",fontFace:"Calibri",isTextBox:true,margin:0});});
s.addShape(pres.ShapeType.roundRect,{x:0.7,y:5.6,w:11.95,h:1.25,rectRadius:0.1,fill:{color:"0A2E43"},line:{color:"1AA3C4",width:1.3}});
s.addText([{text:"一句话结论：",options:{bold:true,color:"7FD4F0",fontSize:16}},{text:"它威胁不到电网，真正的战场在网络层；碎片化 + 检测后立刻隔离，让这类攻击几乎打不出实际损失。",options:{color:"FFFFFF",fontSize:16,bold:true}}],{x:1.0,y:5.6,w:11.4,h:1.25,align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("结论：方法可核查、建模够真、协议是关键、现实指导。一句话：电网不是主战场，网络层才是；碎片化+检测隔离让攻击几乎无损。");

pres.writeFile({fileName:"/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/ppt/deck2.pptx"}).then(fn=>console.log("WROTE",fn));
