const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.defineLayout({ name: "W", width: 13.333, height: 7.5 });
pres.layout = "W";

const THEME = {
  name: "EVsec", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1:"1A2633", lt1:"FFFFFF", dk2:"0F3D57", lt2:"F4F7FB",
    accent1:"1AA3C4", accent2:"E8384F", accent3:"1EA97C", accent4:"8B4DDB",
    accent5:"F08A24", accent6:"5D6B7A", hlink:"1AA3C4", folHlink:"8B4DDB" },
};
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.defineSlideMaster({ title:"LIGHT", background:{ color:"FFFFFF" }, objects:[
  { text:{ text:"巴塞罗那充电网络 · 网络层攻防仿真（面向非专业读者）", options:{ x:0.5,y:7.06,w:9,h:0.3,fontSize:9,color:"9AA7B5",fontFace:"Calibri",isTextBox:true,margin:0 } } },
]});
pres.defineSlideMaster({ title:"DARK", background:{ color:"0F3D57" } });

const FIG = "/home/user/Project1/figs/";
const INK="1A2633", NAVY="0F3D57", TEAL="1AA3C4", RED="E8384F", GREEN="1EA97C", PURPLE="8B4DDB", ORANGE="F08A24", MUT="5D6B7A", CARD="F4F7FB", CARDE="D7E0EA";

function title(s, t){ s.addText(t, { x:0.6,y:0.36,w:12.1,h:0.8, fontSize:30, bold:true, color:NAVY, fontFace:"Cambria", align:"left", valign:"middle", isTextBox:true, margin:0 }); }
function kicker(s, t, col){ s.addText(t, { x:0.62,y:0.18,w:12,h:0.3, fontSize:12, bold:true, color:col||TEAL, fontFace:"Calibri", charSpacing:2, isTextBox:true, margin:0 }); }
function card(s,x,y,w,h,fill){ s.addShape(pres.ShapeType.roundRect,{ x,y,w,h, rectRadius:0.09, fill:{color:fill||CARD}, line:{color:CARDE,width:1}, shadow:{type:"outer",color:"B9C6D4",opacity:0.35,blur:7,offset:2,angle:90} }); }
function stat(s,x,y,w,num,lab,col){
  s.addText(num,{ x,y,w,h:0.9, fontSize:46, bold:true, color:col, fontFace:"Cambria", align:"center", isTextBox:true, margin:0 });
  s.addText(lab,{ x,y:y+0.88,w,h:0.55, fontSize:12.5, color:MUT, fontFace:"Calibri", align:"center", isTextBox:true, margin:0 });
}

// ---------------- Slide 1 — cover (dark) ----------------
let s = pres.addSlide({ masterName:"DARK" });
s.addShape(pres.ShapeType.roundRect,{ x:0.9,y:1.05,w:1.9,h:0.5, rectRadius:0.25, fill:{color:"13506F"}, line:{color:"2E86AD",width:1} });
s.addText("真实数据 · 全程仿真", { x:0.9,y:1.05,w:1.9,h:0.5, fontSize:11, bold:true, color:"8FE3F5", align:"center", valign:"middle", fontFace:"Calibri", isTextBox:true, margin:0 });
s.addText("充电桩会被黑客“远程操纵”吗？", { x:0.9,y:1.9,w:11.5,h:1.5, fontSize:46, bold:true, color:"FFFFFF", fontFace:"Cambria", align:"left", isTextBox:true, margin:0 });
s.addText("用巴塞罗那一座城市的真实数据，做一次“网络层”攻防推演", { x:0.92,y:3.5,w:11.5,h:0.7, fontSize:19, color:"CFE3EF", fontFace:"Calibri", align:"left", isTextBox:true, margin:0 });
s.addText("电动汽车充电网络安全  ·  只在隔离仿真中进行，不接触任何真实系统", { x:0.92,y:4.25,w:11.5,h:0.5, fontSize:13, color:"8CA9BC", fontFace:"Calibri", align:"left", isTextBox:true, margin:0 });
// stat chips
const chips=[["37+","家充电运营商"],["621","个充电点"],["1 整年","真实充电记录"],["39","个独立后台"]];
chips.forEach((c,i)=>{ const x=0.9+i*3.0;
  s.addShape(pres.ShapeType.roundRect,{ x,y:5.45,w:2.7,h:1.25, rectRadius:0.1, fill:{color:"12405B"}, line:{color:"24617E",width:1} });
  s.addText(c[0],{ x,y:5.58,w:2.7,h:0.7, fontSize:30, bold:true, color:"5AD0E8", align:"center", fontFace:"Cambria", isTextBox:true, margin:0 });
  s.addText(c[1],{ x,y:6.28,w:2.7,h:0.35, fontSize:12, color:"B9D3E0", align:"center", fontFace:"Calibri", isTextBox:true, margin:0 });
});
s.addNotes("开场：一句话——我在研究充电桩会不会被黑客通过网络远程操纵，用的是巴塞罗那一整座城市的真实数据，全程只在仿真里做。");

// ---------------- Slide 2 — big picture (framework image) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"一页看懂全局");
s.addImage({ path:FIG+"figLOGIC_framework.png", x:1.17, y:0.72, w:11.0, h:11.0/1.714 });
s.addNotes("这张图就是全文逻辑：问题→关键洞察(碎片化)→怎么研究(一家标定、全城推演)→主要发现→一句话结论。后面逐张展开。");

// ---------------- Slide 3 — the problem (schematic) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"问题", RED);
title(s,"充电桩是怎么被“远程控制”的");
// left text
const p3 = [
  { text:"每一根充电桩，都通过网络连着运营商的“后台”。", options:{bullet:true, color:INK, breakLine:true, paraSpaceAfter:10} },
  { text:"运营商靠这条通道远程给桩下命令：调功率、远程停充、读电表。", options:{bullet:true, color:INK, breakLine:true, paraSpaceAfter:10} },
  { text:"这条通道用的协议叫 OCPP。", options:{bullet:true, color:INK, breakLine:true, paraSpaceAfter:10} },
  { text:"一旦黑客攻破这个后台——就能同时操纵这家公司的所有桩。", options:{bullet:true, color:RED, bold:true, breakLine:true} },
];
s.addText(p3, { x:0.7,y:1.7,w:5.6,h:3.6, fontSize:16, fontFace:"Calibri", align:"left", isTextBox:true, valign:"top", paraSpaceAfter:10 });
s.addShape(pres.ShapeType.roundRect,{ x:0.7,y:5.55,w:5.6,h:1.15, rectRadius:0.08, fill:{color:"FDECEC"}, line:{color:"F3B5B5",width:1} });
s.addText("关键点：攻破 1 个后台 = 操纵这家的全部桩", { x:0.85,y:5.55,w:5.3,h:1.15, fontSize:16, bold:true, color:"B3324C", align:"left", valign:"middle", fontFace:"Calibri", isTextBox:true, margin:0 });
// right schematic
const cx=9.7;
s.addShape(pres.ShapeType.roundRect,{ x:cx-1.5,y:1.75,w:1.6,h:0.6, rectRadius:0.08, fill:{color:RED} });
s.addText("黑客", { x:cx-1.5,y:1.75,w:1.6,h:0.6, fontSize:14, bold:true, color:"FFFFFF", align:"center", valign:"middle", fontFace:"Calibri", isTextBox:true, margin:0 });
s.addShape(pres.ShapeType.roundRect,{ x:cx-1.9,y:3.0,w:2.4,h:0.75, rectRadius:0.08, fill:{color:PURPLE} });
s.addText("运营商后台 CSMS", { x:cx-1.9,y:3.0,w:2.4,h:0.75, fontSize:12.5, bold:true, color:"FFFFFF", align:"center", valign:"middle", fontFace:"Calibri", isTextBox:true, margin:0 });
s.addShape(pres.ShapeType.line,{ x:cx-0.7,y:2.35,w:0,h:0.65, line:{color:RED,width:2.5,endArrowType:"triangle"} });
// piles fan
const piles=[-2.4,-1.4,-0.4,0.6,1.6,2.6];
piles.forEach(dx=>{
  s.addShape(pres.ShapeType.line,{ x:cx-0.7,y:3.75,w: (cx+dx+0.25)-(cx-0.7), h:1.35, line:{color:"F2A3AB",width:1.3} });
});
piles.forEach(dx=>{
  s.addShape(pres.ShapeType.roundRect,{ x:cx+dx-0.25,y:5.1,w:0.5,h:0.7, rectRadius:0.06, fill:{color:TEAL}, line:{color:"117a94",width:1} });
});
s.addText("这家公司的充电桩（全部被控）", { x:cx-2.9,y:5.95,w:5.8,h:0.4, fontSize:12, color:MUT, align:"center", fontFace:"Calibri", isTextBox:true, margin:0 });
s.addNotes("用大白话解释后台(CSMS)和OCPP：运营商远程控制桩的通道。攻破后台=操纵这家所有桩。右边示意图：黑客→后台→一串桩。");

// ---------------- Slide 4 — key insight: fragmentation (city map) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"关键洞察", TEAL);
title(s,"一座城市不是“一张网”");
s.addImage({ path:FIG+"figC1_citymap.png", x:6.4, y:1.35, w:6.5, h:6.5/1.203 });
const p4=[
  { text:"全城是 37+ 家互相独立的后台拼成的。", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:12} },
  { text:"我把这叫“控制平面碎片化”。", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:12} },
  { text:"攻破一家后台，横向只能波及这一家的桩——到不了别家。", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:12} },
  { text:"这天然限制了一次入侵能造成的“爆炸半径”。", options:{bullet:true,color:GREEN,bold:true,breakLine:true} },
];
s.addText(p4,{ x:0.7,y:1.8,w:5.3,h:3.4, fontSize:16.5, fontFace:"Calibri", align:"left", valign:"top", isTextBox:true, paraSpaceAfter:12 });
card(s,0.7,5.35,5.3,1.5,CARD);
stat(s,0.7,5.45,2.6,"39","个互相独立的后台",NAVY);
stat(s,3.4,5.45,2.6,"碎片化","= 天然的安全隔舱",GREEN);
s.addNotes("关键洞察：城市不是一张网，是几十个互不相通的后台。攻一家波及不到别家。地图上每种颜色是一家运营商。");

// ---------------- Slide 5 — method ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"怎么研究", PURPLE);
title(s,"一家真实标定，全城推演");
// two big cards
card(s,0.7,1.7,5.9,4.0,"EEF6FB");
s.addShape(pres.ShapeType.roundRect,{x:0.95,y:1.95,w:2.1,h:0.5,rectRadius:0.2,fill:{color:TEAL}});
s.addText("微观 · 先摸透一家",{x:0.95,y:1.95,w:2.1,h:0.5,fontSize:11.5,bold:true,color:"FFFFFF",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText([
  {text:"只有 AMB 一家有一整年真实充电记录。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"搭了一个“货真价实”的模拟器：真用 OCPP 协议、按真实充电记录运行。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"扮演黑客攻破后台，测出“攻破 → 检测 → 隔离”的全过程。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"还顺便测了：多快能发现、会不会误报。",options:{bullet:true,breakLine:true}},
],{x:0.95,y:2.65,w:5.4,h:2.9,fontSize:15,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,paraSpaceAfter:9});
card(s,6.75,1.7,5.9,4.0,"F1EEFB");
s.addShape(pres.ShapeType.roundRect,{x:7.0,y:1.95,w:2.3,h:0.5,rectRadius:0.2,fill:{color:PURPLE}});
s.addText("宏观 · 再放大全城",{x:7.0,y:1.95,w:2.3,h:0.5,fontSize:11.5,bold:true,color:"FFFFFF",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText([
  {text:"把全城 621 个充电点真的连成 39 个独立后台。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"用这家测出的规律，按每家规模推广到全城。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"做三组实验：攻破一家 / 协同攻破多家 / 各种攻击×各种防御。",options:{bullet:true,breakLine:true,paraSpaceAfter:9}},
  {text:"得到可在真实地图上逐时回放的全城结论。",options:{bullet:true,breakLine:true}},
],{x:7.0,y:2.65,w:5.4,h:2.9,fontSize:15,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,paraSpaceAfter:9});
s.addShape(pres.ShapeType.roundRect,{x:0.7,y:5.95,w:11.95,h:0.8,rectRadius:0.08,fill:{color:"E9F6EF"},line:{color:"A8D9C2",width:1}});
s.addText("全程只在隔离仿真里完成，不接触任何真实运营商后台或充电桩。",{x:0.7,y:5.95,w:11.95,h:0.8,fontSize:14.5,bold:true,color:"1C7A57",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("方法：一家标定(真数据真协议) + 全城推演(621桩连成39个后台)。强调全程仿真、不碰真实系统。");

// ---------------- Slide 6 — result 1: blast radius (figC2) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"实验结果 ①", RED);
title(s,"攻破一家后台，能波及多大");
s.addImage({ path:FIG+"figC2_blast_single.png", x:0.7, y:1.5, w:8.4, h:8.4/1.737 });
stat(s,9.4,1.85,3.3,"17%","攻破最大一家 = 全城充电功率",RED);
stat(s,9.4,3.55,3.3,"0.16%","换算到电网，仅占峰值",NAVY);
s.addShape(pres.ShapeType.roundRect,{x:9.4,y:5.15,w:3.3,h:1.5,rectRadius:0.08,fill:{color:CARD},line:{color:CARDE,width:1}});
s.addText("两家功率相近，覆盖面却差很多：Endesa 波及 18 个城镇，BSM 只在市中心 3 个城镇。",{x:9.55,y:5.25,w:3.0,h:1.3,fontSize:13,color:INK,align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("结果1：攻破最大一家只占全城17%、对电网0.16%。地图对比：覆盖面(Endesa 18城镇)和集中度(BSM 3城镇)不一样。");

// ---------------- Slide 7 — result 2: coordinated campaign (native chart) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"实验结果 ②", ORANGE);
title(s,"同时攻破好几家呢");
const labels=["1","2","3","4","5","6","7","8"];
const chartData=[
  { name:"无防御：被发现前受控电量", labels, values:[3928,6044,8159,10683,11889,12216,12963,13705] },
  { name:"检测+隔离：被发现前受控电量", labels, values:[6.6,11.2,20.9,23.6,26.5,28,31.5,33.7] },
];
s.addChart(pres.ChartType.line, chartData, {
  x:0.7,y:1.6,w:7.9,h:5.2, chartColors:[RED,GREEN], lineSize:3, lineDataSymbol:"circle", lineDataSymbolSize:6,
  showLegend:true, legendPos:"b", legendColor:INK, legendFontSize:11, legendFontFace:"+mn-lt",
  showTitle:false, showValue:false,
  catAxisTitle:"同时攻破的后台数 k（按功率从大到小）", showCatAxisTitle:true, catAxisTitleColor:MUT, catAxisTitleFontSize:12, catAxisTitleFontFace:"+mn-lt",
  valAxisTitle:"受控电量（度/kWh）", showValAxisTitle:true, valAxisTitleColor:MUT, valAxisTitleFontSize:12, valAxisTitleFontFace:"+mn-lt",
  catAxisLabelColor:MUT, valAxisLabelColor:MUT, catAxisLabelFontSize:11, valAxisLabelFontSize:11, catAxisLabelFontFace:"+mn-lt", valAxisLabelFontFace:"+mn-lt",
  valGridLine:{ color:"E5EBF1", size:1 }, catGridLine:{ style:"none" },
});
const p7=[
  {text:"要接近全城，得同时攻破很多家后台——", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:11}},
  {text:"而且是“相互独立”的多次攻破，一次搞不定。", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:11}},
  {text:"红线一路飙升，绿线始终贴着地面——", options:{bullet:true,color:INK,breakLine:true,paraSpaceAfter:11}},
  {text:"只要逐家“检测+隔离”，损失一直压在几十度。", options:{bullet:true,color:GREEN,bold:true,breakLine:true}},
];
s.addText(p7,{ x:8.85,y:1.85,w:3.85,h:3.6, fontSize:14.5, fontFace:"Calibri", align:"left", valign:"top", isTextBox:true, paraSpaceAfter:11 });
card(s,8.85,5.5,3.85,1.2,CARD);
s.addText([{text:"协同攻破前 5 家（44.9 MW）\n",options:{color:MUT,fontSize:12}},{text:"11889 度 → 隔离后仅 26.5 度",options:{color:RED,bold:true,fontSize:15}}],{x:9.0,y:5.5,w:3.55,h:1.2,align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("结果2：协同攻破累加，但接近全城需很多次独立攻破(难)；红线飙升、绿线贴地——逐家隔离一直把损失压到几十度。");

// ---------------- Slide 8 — result 3: defense works (storyboard) ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"实验结果 ③", GREEN);
title(s,"检测到就隔离：约 1 分钟止损");
s.addImage({ path:FIG+"figC5_storyboard.png", x:0.6, y:1.45, w:12.1, h:12.1/3.067 });
// three outcome chips
const d8=[["99%+","损失削减幅度",GREEN],["≈1 分钟","发现并隔离",TEAL],["0","良性回放误报",NAVY]];
d8.forEach((c,i)=>{ const x=0.9+i*4.1; card(s,x,5.75,3.7,1.15,CARD);
  s.addText(c[0],{x,y:5.82,w:3.7,h:0.65,fontSize:30,bold:true,color:c[2],align:"center",fontFace:"Cambria",isTextBox:true,margin:0});
  s.addText(c[1],{x,y:6.45,w:3.7,h:0.35,fontSize:12.5,color:MUT,align:"center",fontFace:"Calibri",isTextBox:true,margin:0});
});
s.addNotes("结果3：光检测没用，必须隔离。检测到就隔离那家后台，约1分钟把损失降99%以上；良性回放零误报。图是攻防四帧：扩散→最大→隔离(变绿)。");

// ---------------- Slide 9 — two extra takeaways ----------------
s = pres.addSlide({ masterName:"LIGHT" });
kicker(s,"两个额外要点", TEAL);
title(s,"会“测谎”，也看清了对电网的影响");
// card A: detector
card(s,0.7,1.7,5.9,4.9,"EEF6FB");
s.addShape(pres.ShapeType.roundRect,{x:0.95,y:1.95,w:2.6,h:0.5,rectRadius:0.2,fill:{color:TEAL}});
s.addText("一个靠谱的“测谎器”",{x:0.95,y:1.95,w:2.6,h:0.5,fontSize:11.5,bold:true,color:"FFFFFF",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText([
  {text:"用“规模×节律”判断什么才算异常。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"2025 年 4 月西班牙大停电：全网一起降 → 判为真实事件，不误报。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"黑客在单个站点伪造电表：只有一处异常 → 报警。",options:{bullet:true,breakLine:true,paraSpaceAfter:10}},
  {text:"关键：它不会把真实大停电错当成攻击。",options:{bullet:true,bold:true,color:"0E7E90",breakLine:true}},
],{x:0.95,y:2.65,w:5.4,h:3.7,fontSize:15,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true,paraSpaceAfter:10});
// card B: grid
card(s,6.75,1.7,5.9,4.9,"F4F7FB");
s.addShape(pres.ShapeType.roundRect,{x:7.0,y:1.95,w:2.6,h:0.5,rectRadius:0.2,fill:{color:NAVY}});
s.addText("对电网只是“毛毛雨”",{x:7.0,y:1.95,w:2.6,h:0.5,fontSize:11.5,bold:true,color:"FFFFFF",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText("就算全城充电都被控制，也只占电网峰值的 0.16%，远低于会让电网出事的 9–11%。",{x:7.0,y:2.6,w:5.4,h:1.1,fontSize:15,color:INK,fontFace:"Calibri",align:"left",valign:"top",isTextBox:true});
// mini bar 0..12%
const bx=7.1, bw=5.1, by=4.75;
s.addShape(pres.ShapeType.rect,{x:bx,y:by,w:bw,h:0.26,fill:{color:"E3EAF1"}});
s.addShape(pres.ShapeType.rect,{x:bx+bw*(9/12),y:by,w:bw*(2/12),h:0.26,fill:{color:"F0C28A"}}); // 9-11% band
s.addShape(pres.ShapeType.rect,{x:bx,y:by,w:Math.max(0.05,bw*(0.16/12)),h:0.26,fill:{color:RED}});   // 0.16%
s.addText("0.16%（全城充电）",{x:bx-0.1,y:by+0.3,w:3.2,h:0.3,fontSize:11,bold:true,color:RED,align:"left",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText("9–11%（电网出事阈值）",{x:bx+bw*0.5,y:by+0.3,w:2.7,h:0.3,fontSize:11,bold:true,color:"C9872F",align:"right",fontFace:"Calibri",isTextBox:true,margin:0});
s.addText("占电网峰值的比例 →",{x:bx,y:by-0.35,w:5.1,h:0.3,fontSize:10.5,color:MUT,align:"left",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("额外要点1：测谎器区分真停电vs黑客造假。要点2：就算全城被控也只占电网0.16%，远低于9-11%出事阈值——所以电网不是主战场。");

// ---------------- Slide 10 — value & conclusion (dark) ----------------
s = pres.addSlide({ masterName:"DARK" });
s.addText("价值与意义", { x:0.7,y:0.5,w:12,h:0.7, fontSize:30, bold:true, color:"FFFFFF", fontFace:"Cambria", isTextBox:true, margin:0 });
const vals=[
  ["填补空白","第一次用一座真城市的真数据+真协议，把抽象的“控制了电网x%”拆成可核查的网络层问题。",TEAL],
  ["现实指导","真正该防的是网络层后台通道，不是电网；城市“多家分散”本身就是安全资产，别盲目追求统一大平台。",GREEN],
  ["可移植","欧盟每座城市都有同样的登记表，这套“一家标定、全城推演”直接能用。",ORANGE],
  ["可视化","所有结论能在真实地图上按时间、按运营商回放，还有交互式指挥台，非专业人也能看懂。",PURPLE],
];
vals.forEach((v,i)=>{ const col=i%2, row=Math.floor(i/2); const x=0.7+col*6.1, y=1.5+row*1.95;
  s.addShape(pres.ShapeType.roundRect,{x,y,w:5.85,h:1.75,rectRadius:0.09,fill:{color:"12405B"},line:{color:"24617E",width:1}});
  s.addShape(pres.ShapeType.roundRect,{x:x+0.2,y:y+0.22,w:1.55,h:0.45,rectRadius:0.22,fill:{color:v[2]}});
  s.addText(v[0],{x:x+0.2,y:y+0.22,w:1.55,h:0.45,fontSize:12.5,bold:true,color:"0F3D57",align:"center",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
  s.addText(v[1],{x:x+0.2,y:y+0.72,w:5.45,h:0.95,fontSize:13,color:"DCEAF2",align:"left",valign:"top",fontFace:"Calibri",isTextBox:true,margin:0});
});
s.addShape(pres.ShapeType.roundRect,{x:0.7,y:5.6,w:11.95,h:1.25,rectRadius:0.1,fill:{color:"0A2E43"},line:{color:"1AA3C4",width:1.3}});
s.addText([{text:"一句话结论：",options:{bold:true,color:"7FD4F0",fontSize:16}},{text:"它威胁不到电网，真正的战场在网络层；城市的碎片化 + 检测后立刻隔离，让这类攻击几乎打不出实际损失。",options:{color:"FFFFFF",fontSize:16,bold:true}}],{x:1.0,y:5.6,w:11.4,h:1.25,align:"left",valign:"middle",fontFace:"Calibri",isTextBox:true,margin:0});
s.addNotes("价值：填空白/现实指导/可移植/可视化。一句话收尾：电网不是主战场，网络层才是；碎片化+检测隔离让攻击几乎无损。");

pres.writeFile({ fileName: "/tmp/claude-0/-home-user-Project1/ea5e1e39-6abb-5644-803d-3dfb3ca78b4c/scratchpad/ppt/deck.pptx" }).then(fn=>console.log("WROTE",fn));
