"""
残矿回收智能决策支持系统 v2.0
Residual Ore Recovery Intelligent Decision Support System
支持中英文双语切换 / Bilingual Chinese-English Support
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from modules.hazard import calculate_W
from modules.rvi import calculate_RVI
from modules.feasibility import calculate_FI
from modules.backfill_method import recommend_methods
from modules.material import select_material
from modules.economic import calculate_economics
from modules.knn_cbr import knn_recommend, dual_path_fusion
from modules.cloud_model import cloud_hazard_simulation
from modules.monte_carlo import monte_carlo_economic
from modules.sensitivity import run_hazard_sensitivity, run_economic_sensitivity
from modules.report import generate_excel_report
from modules.i18n import t, tr, tr_dict, tr_list_of_dicts
import numpy as np
from datetime import datetime

st.set_page_config(page_title="Residual Ore DSS", page_icon="⛏️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
.main-header{font-size:1.8rem;font-weight:bold;text-align:center;padding:1rem 0;
  background:linear-gradient(135deg,#1B2A4A 0%,#2E75B6 50%,#548235 100%);
  color:white;border-radius:12px;margin-bottom:1rem}
.main-header small{font-size:0.7rem;opacity:0.85}
div[data-testid="stMetric"]{background:#f8f9fa;border-radius:8px;padding:0.8rem;border-left:4px solid #2E75B6}
</style>""", unsafe_allow_html=True)

# ---- Language ----
with st.sidebar:
    lang = st.selectbox("🌐 语言 / Language", ['中文','English'], index=0)
    L = 'zh' if lang == '中文' else 'en'

st.markdown(f'<div class="main-header">⛏️ {t("app_title",L)}<br><small>{t("app_subtitle",L)}</small></div>', unsafe_allow_html=True)

# ---- Bilingual select helper ----
def sel(label, options, idx=1):
    display = [o[0] for o in options]
    choice = st.selectbox(label, display, index=idx)
    return next(o[1] for o in options if o[0] == choice)

G4 = [(t('favorable',L),'有利'),(t('moderate',L),'一般'),(t('unfavorable',L),'不利')]
G6 = [(t('good',L),'好'),(t('moderate',L),'一般'),(t('not_good',L),'不好')]
G13 = [(t('good',L),'好'),(t('medium',L),'中等'),(t('poor',L),'差')]
M5 = [(t('open_stoping',L),'空场法'),(t('caving',L),'崩落法'),(t('backfill',L),'充填法'),(t('shrinkage',L),'留矿法'),(t('room_pillar',L),'房柱法')]
M6 = [(t('support_good',L),'好'),(t('support_moderate',L),'一般'),(t('support_none',L),'不支护')]
M7 = [(t('blast_large',L),'大药量爆破'),(t('blast_medium',L),'中等药量爆破'),(t('blast_small',L),'小药量爆破')]
M9 = [(t('instability_none',L),'无'),(t('instability_once',L),'一次'),(t('instability_multi',L),'多次')]
POL = [(t('policy_mandatory',L),'明确要求充填'),(t('policy_encourage',L),'鼓励但不强制'),(t('policy_none',L),'无明确要求')]

# ---- Sidebar Inputs ----
with st.sidebar:
    st.header(t('sidebar_title',L))
    st.subheader(t('sec_basic',L))
    mine_name = st.text_input(t('mine_name',L), "某金矿" if L=='zh' else "Gold Mine A")
    ore_type = st.selectbox(t('ore_type',L), ['Au','Fe','Cu','Pb-Zn','W'])

    st.subheader(t('sec_geo',L))
    thickness=st.number_input(t('G1',L),0.5,100.0,5.0,0.5); dip_angle=st.number_input(t('G2',L),0,90,45)
    depth=st.number_input(t('G3',L),10,3000,300,10); so=sel(t('G4',L),G4,1)
    js=st.number_input(t('G5',L),0.01,5.0,0.5,0.1); jc=sel(t('G6',L),G6,1)
    rqd=st.number_input(t('G7',L),0,100,65); em=st.number_input(t('G8',L),1000,100000,30000,1000)
    rur=st.number_input(t('G9',L),5,300,80,5); ou=st.number_input(t('G10',L),5,300,80,5)
    sd=st.number_input(t('G11',L),0,50,10); sdir=sel(t('G12',L),G4,1)
    gw=sel(t('G13',L),G13,1)

    st.subheader(t('sec_mining',L))
    ma=st.number_input(t('M1',L),1000,500000,50000,1000); gv=st.number_input(t('M2',L),1000,5000000,500000,10000)
    par=st.number_input(t('M3',L),0,60,20); pwr=st.number_input(t('M4',L),0.1,10.0,2.0,0.1)
    mm=sel(t('M5',L),M5,0); rs=sel(t('M6',L),M6,1); bl=sel(t('M7',L),M7,1)
    rm=st.number_input(t('M8',L),1,5,1); gi=sel(t('M9',L),M9,0)

    st.subheader(t('sec_resource',L))
    grade=st.number_input(t('grade',L),0.1,100.0,3.35,0.1); reserve=st.number_input(t('reserve',L),1000,1000000,78000,1000)
    rec_rate=st.slider(t('recovery_rate',L),30,95,75)/100; gp=st.number_input(t('gold_price',L),100,800,450,10)
    mc=st.number_input(t('mining_cost',L),10,500,120,5); pc=st.number_input(t('processing_cost',L),10,300,80,5)
    hs=st.checkbox(t('has_station',L),True); ic=st.checkbox(t('is_cyanide',L),False)
    pol=sel(t('policy_req',L),POL,1)
    st.divider()
    run = st.button(t('run_btn',L), type="primary", use_container_width=True)

# ---- MAIN ----
if run:
    geo_p=dict(thickness=thickness,dip_angle=dip_angle,depth=depth,structure_orientation=so,
               joint_spacing=js,joint_condition=jc,rqd=rqd,elastic_modulus=em,
               rock_ucs_roof=rur,ore_ucs=ou,stress_diff=sd,stress_direction=sdir,groundwater=gw)
    min_p=dict(mining_area=ma,goaf_volume=gv,pillar_area_ratio=par,pillar_wh_ratio=pwr,
               mining_method=mm,roof_support=rs,blasting=bl,repeated_mining=rm,goaf_instability=gi)

    w=calculate_W(geo_p,min_p); rvi=calculate_RVI(grade,reserve,depth,ore_type)
    fi=calculate_FI(thickness,grade*gp,mc+pc,pol)
    meth=recommend_methods(dip_angle,thickness,depth,w['W'],mm,hs)
    mat=select_material(meth['top1_method'],ic,not ic)
    bfc=mat['top3'][0]['cost'] if mat['top3'] else 40
    econ=calculate_economics(reserve,grade,rec_rate,gp,mc,pc,bfc,hs)
    gs='大' if gv>=500000 else ('中' if gv>=100000 else '小')
    gl='高' if grade>=3 else ('中' if grade>=1 else '低')
    knn=knn_recommend(thickness,dip_angle,depth,rqd,mm,gs,gl,ore_type=ore_type)
    fus=dual_path_fusion(meth,knn)
    # Cloud Model simulation
    cloud_res=cloud_hazard_simulation(geo_p,min_p,calculate_W,n_simulations=1000)
    # Monte Carlo simulation
    mc_res=monte_carlo_economic(reserve,grade,rec_rate,gp,mc,pc,bfc,hs,n_simulations=5000)
    # Sensitivity analysis
    sa_w=run_hazard_sensitivity(geo_p,min_p,calculate_W)
    econ_sa_params=dict(reserve=reserve,grade=grade,recovery_rate=rec_rate,gold_price=gp,
                        mining_cost=mc,processing_cost=pc,backfill_cost=bfc,has_station=hs)
    sa_npv=run_economic_sensitivity(econ_sa_params,calculate_economics)
    lc={'A':'🟢','B':'🟡','C':'🔴'}

    # ---- 翻译所有模块输出 ----
    w['level_name']=tr(w['level_name'],L); w['level']=tr(w['level'],L); w['suggestion']=tr(w['suggestion'],L)
    w['details_W1']=tr_list_of_dicts(w['details_W1'],['因素','输入值'],L)
    w['details_W2']=tr_list_of_dicts(w['details_W2'],['因素','输入值'],L)
    rvi['level']=tr(rvi['level'],L)
    fi['level']=tr(fi['level'],L); fi['suggestion']=tr(fi['suggestion'],L)
    for m in meth['top3']+meth['all_results']:
        m['method']=tr(m['method'],L); m['pros']=tr(m['pros'],L); m['cons']=tr(m['cons'],L)
        m['breakdown']={tr(k,L):v for k,v in m['breakdown'].items()}
    meth['top1_method']=tr(meth['top1_method'],L)
    for m in mat['top3']+mat['all_candidates']:
        m['material']=tr(m['material'],L); m['features']=tr(m['features'],L)
    for f in mat['filtered_out']:
        f['material']=tr(f['material'],L); f['reason']=tr(f['reason'],L)
    econ['eval_level']=tr(econ['eval_level'],L)
    for m in knn['top3']:
        m['method']=tr(m['method'],L)
    knn['top1_method']=tr(knn['top1_method'],L)
    for c in knn['similar_cases']:
        c['original_method']=tr(c['original_method'],L); c['backfill_method']=tr(c['backfill_method'],L)
    fus['method']=tr(fus['method'],L)
    # 重建融合消息（使用翻译后的方法名）
    _k1=meth['top1_method']; _d1=knn['top1_method']
    if L=='zh':
        msg=fus['message_zh']
    else:
        if fus['level']=='A':
            msg=f'Both paths agree on [{_k1}] as Top-1. High confidence, strongly recommended.'
        elif fus['level']=='B':
            msg=f'Knowledge path: [{_k1}], Data path: [{_d1}]. Partial agreement, compare candidates.'
        else:
            msg=f'Paths disagree (Knowledge: {_k1} vs Data: {_d1}). Expert review suggested.'

    tabs=st.tabs([t('tab_overview',L),t('tab_hazard',L),t('tab_rvi',L),t('tab_fi',L),
                  t('tab_method',L),t('tab_material',L),t('tab_economic',L),t('tab_dual_path',L),
                  '☁️ Cloud Model' if L=='en' else '☁️ 云模型',
                  '🎲 Monte Carlo' if L=='en' else '🎲 蒙特卡洛',
                  '📈 Sensitivity' if L=='en' else '📈 敏感性分析',
                  '📄 Report' if L=='en' else '📄 报告导出'])

    with tabs[0]:
        st.subheader(f"📊 {mine_name} — {t('report_title',L)}")
        c1,c2,c3=st.columns(3)
        c1.metric(t('hazard_index',L),f"{w['W']:.3f}",w['level_name'])
        c2.metric(t('rvi_index',L),f"{rvi['RVI']:.3f}",rvi['level'])
        c3.metric(t('fi_index',L),f"{fi['FI']:.3f}",fi['level'])
        st.divider()
        c4,c5=st.columns(2)
        c4.metric(t('recommended_method',L),meth['top1_method'],f"{t('match_score',L)} {meth['top1_score']}{t('points',L)}")
        if mat['top3']: c5.metric(t('recommended_material',L),mat['top3'][0]['material'],f"{mat['top3'][0]['cost']}{t('yuan_per_t',L)}")
        st.divider()
        c6,c7,c8,c9=st.columns(4)
        c6.metric(t('npv',L),f"{econ['npv_wan']:.0f}{t('wan_yuan',L)}")
        c7.metric(t('roi',L),f"{econ['roi']:.1f}%")
        pp=econ['payback_period']; c8.metric(t('payback',L),f"{pp}{t('year',L)}" if isinstance(pp,(int,float)) else str(pp))
        c9.metric(t('economic_eval',L),econ['eval_level'])
        st.divider()
        if fus['level']=='A': st.success(f"{lc['A']} {t('dual_path_title',L)}：{msg}")
        elif fus['level']=='B': st.warning(f"{lc['B']} {t('dual_path_title',L)}：{msg}")
        else: st.error(f"{lc['C']} {t('dual_path_title',L)}：{msg}")
        st.subheader(t('radar_title',L))
        fig=go.Figure(data=go.Scatterpolar(r=[1-w['W'],rvi['RVI'],fi['FI']],
            theta=[t('safety',L),t('value',L),t('feasibility',L)],
            fill='toself',line_color='#2E75B6',fillcolor='rgba(46,117,182,0.3)'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),showlegend=False,height=400)
        st.plotly_chart(fig,use_container_width=True,key="radar_overview")

    with tabs[1]:
        st.subheader(t('tab_hazard',L))
        c1,c2,c3=st.columns(3)
        c1.metric(t('geo_hazard',L),f"{w['W1']:.4f}"); c2.metric(t('mining_hazard',L),f"{w['W2']:.4f}")
        em2={'green':'🟢','yellow':'🟡','orange':'🟠','red':'🔴'}
        c3.metric(f"{t('hazard_index',L)} {em2.get(w['color'],'')}",f"{w['W']:.4f}",f"{w['level']} {w['level_name']}")
        if w['color'] in ['red','orange']: st.error(f"⚠️ {w['suggestion']}")
        elif w['color']=='yellow': st.warning(f"⚠️ {w['suggestion']}")
        else: st.success(f"✅ {w['suggestion']}")
        st.divider()
        ca,cb=st.columns(2)
        with ca:
            st.write(f"**{t('geo_detail',L)}**")
            df1=pd.DataFrame(w['details_W1']); df1.columns=[t('factor',L),t('input_value',L),t('score',L),t('max_score',L)]
            st.dataframe(df1,use_container_width=True,hide_index=True)
        with cb:
            st.write(f"**{t('mining_detail',L)}**")
            df2=pd.DataFrame(w['details_W2']); df2.columns=[t('factor',L),t('input_value',L),t('score',L),t('max_score',L)]
            st.dataframe(df2,use_container_width=True,hide_index=True)
        raw=pd.DataFrame(w['details_W1'])
        xcol=raw.columns[0]; ycols=[raw.columns[2],raw.columns[3]]
        fig=px.bar(raw,x=xcol,y=ycols,barmode='group',title=t('geo_chart',L),color_discrete_sequence=['#E74C3C','#BDC3C7'])
        st.plotly_chart(fig,use_container_width=True,key="hazard_bar")

    with tabs[2]:
        st.subheader(t('tab_rvi',L)); st.metric(t('rvi_index',L),f"{rvi['RVI']:.4f}",rvi['level'])
        c1,c2,c3=st.columns(3)
        c1.metric(t('grade_score',L),f"{rvi['Sg']:.2f}",f"{t('weight',L)} 0.40")
        c2.metric(t('reserve_score',L),f"{rvi['Sr']:.2f}",f"{t('weight',L)} 0.35")
        c3.metric(t('depth_score',L),f"{rvi['Sd']:.2f}",f"{t('weight',L)} 0.25")
        fig=go.Figure(data=[go.Pie(labels=[t('grade_contrib',L),t('reserve_contrib',L),t('depth_contrib',L)],
            values=[0.4*rvi['Sg'],0.35*rvi['Sr'],0.25*rvi['Sd']],marker_colors=['#E74C3C','#3498DB','#2ECC71'],hole=0.4)])
        fig.update_layout(title=t('rvi_contribution',L),height=350); st.plotly_chart(fig,use_container_width=True,key="rvi_pie")

    with tabs[3]:
        st.subheader(t('tab_fi',L)); st.metric(t('fi_index',L),f"{fi['FI']:.4f}",f"{fi['level']} — {fi['suggestion']}")
        c1,c2,c3=st.columns(3)
        c1.metric(t('tech_fi',L),f"{fi['St']:.2f}",f"{t('weight',L)} 0.35")
        c2.metric(t('econ_fi',L),f"{fi['Se']:.2f}",f"{t('weight',L)} 0.45")
        c3.metric(t('policy_fi',L),f"{fi['Sp']:.2f}",f"{t('weight',L)} 0.20")
        fig=go.Figure(data=[go.Bar(y=[t('tech_fi',L),t('econ_fi',L),t('policy_fi',L)],
            x=[fi['St'],fi['Se'],fi['Sp']],orientation='h',marker_color=['#3498DB','#E74C3C','#2ECC71'])])
        fig.update_layout(title=t('fi_scores',L),xaxis_range=[0,1],height=300); st.plotly_chart(fig,use_container_width=True,key="fi_bar")

    with tabs[4]:
        st.subheader(t('method_title',L))
        for i,m in enumerate(meth['top3']):
            md=['🥇','🥈','🥉'][i]
            with st.expander(f"{md} {t('rank',L,i=i+1)}：{m['method']}（{m['score']}{t('points',L)}）",expanded=(i==0)):
                c1,c2=st.columns(2)
                with c1:
                    st.write(f"**{t('expected_recovery',L)}：** {m['recovery_rate']}")
                    st.write(f"**{t('pros',L)}：** {m['pros']}"); st.write(f"**{t('cons',L)}：** {m['cons']}")
                with c2:
                    bd=m['breakdown']
                    fig=go.Figure(data=[go.Bar(x=list(bd.keys()),y=list(bd.values()),
                        marker_color=['#2E75B6','#E74C3C','#2ECC71','#F39C12','#9B59B6'])])
                    fig.update_layout(title=t('score_breakdown',L),height=250); st.plotly_chart(fig,use_container_width=True,key=f"method_bd_{i}")
        st.divider(); st.write(f"**{t('all_methods_compare',L)}**")
        adf=pd.DataFrame([{'Method':m['method'],'Score':m['score']} for m in meth['all_results']])
        fig=px.bar(adf,x='Method',y='Score',color='Score',color_continuous_scale='RdYlGn',title=t('method_rank_chart',L))
        st.plotly_chart(fig,use_container_width=True,key="method_all_compare")

    with tabs[5]:
        st.subheader(t('material_title',L))
        if mat['filter_count']>0:
            st.warning(t('filter_warning',L,n=mat['filter_count']))
            for f in mat['filtered_out']: st.caption(f"  ❌ {f['material']}：{f['reason']}")
        for i,m in enumerate(mat['top3'][:3]):
            md=['🥇','🥈','🥉'][i]
            st.info(f"{md} **{m['material']}** — {t('score',L)}: {m['score']}{t('points',L)} | "
                    f"{t('strength',L)}: {m['strength']} | {t('cost_per_t',L)}: {m['cost']}{t('yuan_per_t',L)} | {m['features']}")

    with tabs[6]:
        st.subheader(t('econ_title',L))
        c1,c2,c3,c4=st.columns(4)
        c1.metric(t('metal_output',L),f"{econ['metal_output_kg']:.1f} kg")
        c2.metric(t('total_revenue',L),f"{econ['revenue_wan']:.0f}{t('wan_yuan',L)}")
        c3.metric(t('total_cost',L),f"{econ['total_cost_wan']:.0f}{t('wan_yuan',L)}")
        c4.metric(t('npv',L),f"{econ['npv_wan']:.0f}{t('wan_yuan',L)}",f"{t('profit_rate',L)} {econ['profit_rate']:.1f}%")
        st.divider()
        c5,c6,c7=st.columns(3)
        c5.metric(t('initial_invest',L),f"{econ['initial_investment_wan']:.0f}{t('wan_yuan',L)}",
                  t('has_station_label',L) if hs else t('need_station_label',L))
        pp=econ['payback_period']; c6.metric(t('payback',L),f"{pp} {t('year',L)}" if isinstance(pp,(int,float)) else str(pp))
        c7.metric(t('roi',L),f"{econ['roi']:.1f}%")
        fig=go.Figure(data=[go.Pie(labels=[t('mining_cost_label',L),t('processing_cost_label',L),t('backfill_cost_label',L)],
            values=[econ['mining_cost_wan'],econ['processing_cost_wan'],econ['backfill_cost_wan']],
            marker_colors=['#E74C3C','#3498DB','#2ECC71'],hole=0.4)])
        fig.update_layout(title=t('cost_breakdown',L),height=350); st.plotly_chart(fig,use_container_width=True,key="econ_pie")
        lvl=econ['eval_level']
        if econ['color']=='green': st.success(t('econ_excellent',L,level=lvl))
        elif econ['color']=='blue': st.info(t('econ_good',L,level=lvl))
        elif econ['color']=='orange': st.warning(t('econ_moderate',L,level=lvl))
        else: st.error(t('econ_poor',L,level=lvl))

    with tabs[7]:
        st.subheader(t('dual_path_title',L))
        if fus['level']=='A': st.success(f"{lc['A']} {msg}")
        elif fus['level']=='B': st.warning(f"{lc['B']} {msg}")
        else: st.error(f"{lc['C']} {msg}")
        st.divider()
        c1,c2=st.columns(2)
        with c1:
            st.write(f"### 📚 {t('knowledge_path',L)}")
            for i,m in enumerate(meth['top3']): st.write(f"{'🥇🥈🥉'[i]} {m['method']} — {m['score']}{t('points',L)}")
        with c2:
            st.write(f"### 🤖 {t('data_path',L)}")
            for i,m in enumerate(knn['top3']): st.write(f"{'🥇🥈🥉'[i]} {m['method']} — {t('confidence',L)}: {m['confidence']}%")
        st.divider()
        st.write(f"### 🔍 {t('similar_cases',L)}")
        if knn['similar_cases']: st.dataframe(pd.DataFrame(knn['similar_cases']),use_container_width=True,hide_index=True)

    # --- TAB 8: CLOUD MODEL ---
    with tabs[8]:
        _t = lambda zh,en: zh if L=='zh' else en
        st.subheader(_t('☁️ 云模型不确定性量化','☁️ Cloud Model Uncertainty Quantification'))
        st.caption(_t(f'基于{cloud_res["n_simulations"]}次蒙特卡洛模拟，对关键地质参数施加云模型不确定性',
                       f'Based on {cloud_res["n_simulations"]} Monte Carlo simulations with cloud model uncertainty on key geological parameters'))

        c1,c2,c3,c4=st.columns(4)
        c1.metric(_t('确定性 W','Deterministic W'),f"{w['W']:.4f}")
        c2.metric(_t('W 均值','W Mean'),f"{cloud_res['W_mean']:.4f}",f"±{cloud_res['W_std']:.4f}")
        c3.metric(_t('95%置信下限','95% CI Lower'),f"{cloud_res['W_ci_lower']:.4f}")
        c4.metric(_t('95%置信上限','95% CI Upper'),f"{cloud_res['W_ci_upper']:.4f}")

        st.divider()
        c1,c2=st.columns(2)
        with c1:
            st.write(f"**{_t('W分布直方图','W Distribution Histogram')}**")
            fig=go.Figure(data=[go.Histogram(x=cloud_res['W_samples'],nbinsx=40,
                marker_color='rgba(46,117,182,0.7)',marker_line_color='#1B2A4A',marker_line_width=1)])
            fig.add_vline(x=w['W'],line_dash='dash',line_color='red',
                          annotation_text=_t('确定值','Deterministic'),annotation_position='top right')
            fig.add_vline(x=cloud_res['W_ci_lower'],line_dash='dot',line_color='green')
            fig.add_vline(x=cloud_res['W_ci_upper'],line_dash='dot',line_color='green')
            fig.update_layout(xaxis_title='W',yaxis_title=_t('频次','Frequency'),height=350,showlegend=False)
            st.plotly_chart(fig,use_container_width=True,key='cloud_hist')

        with c2:
            st.write(f"**{_t('危险等级概率分布','Hazard Level Probability Distribution')}**")
            lp=cloud_res['level_probabilities']
            fig=go.Figure(data=[go.Bar(
                x=[f"{_t('Ⅰ级','Lv Ⅰ')}\n(≥0.8)",f"{_t('Ⅱ级','Lv Ⅱ')}\n(0.55-0.8)",
                   f"{_t('Ⅲ级','Lv Ⅲ')}\n(0.3-0.55)",f"{_t('Ⅳ级','Lv Ⅳ')}\n(<0.3)"],
                y=[lp['Ⅰ'],lp['Ⅱ'],lp['Ⅲ'],lp['Ⅳ']],
                marker_color=['#E74C3C','#F39C12','#F1C40F','#2ECC71'],
                text=[f"{lp['Ⅰ']}%",f"{lp['Ⅱ']}%",f"{lp['Ⅲ']}%",f"{lp['Ⅳ']}%"],textposition='outside')])
            fig.update_layout(yaxis_title=_t('概率 (%)','Probability (%)'),height=350)
            st.plotly_chart(fig,use_container_width=True,key='cloud_level_prob')

        st.divider()
        st.write(f"**{_t('各参数云模型参数','Cloud Model Parameters for Each Variable')}**")
        cloud_df_data=[]
        for k,v in cloud_res['cloud_params'].items():
            cloud_df_data.append({
                _t('参数','Parameter'): v['name_zh'] if L=='zh' else v['name_en'],
                _t('单位','Unit'): v['unit'],
                'Ex': v['Ex'], 'En': v['En'], 'He': v['He'],
                _t('不确定性','Uncertainty'): v['level'].capitalize()
            })
        st.dataframe(pd.DataFrame(cloud_df_data),use_container_width=True,hide_index=True)

    # --- TAB 9: MONTE CARLO ---
    with tabs[9]:
        _t = lambda zh,en: zh if L=='zh' else en
        st.subheader(_t('🎲 Monte Carlo 经济风险模拟','🎲 Monte Carlo Economic Risk Simulation'))
        st.caption(_t(f'基于{mc_res["n_simulations"]}次随机模拟',f'Based on {mc_res["n_simulations"]} random simulations'))

        c1,c2,c3,c4=st.columns(4)
        c1.metric(_t('NPV均值','NPV Mean'),f"{mc_res['npv_mean']:.0f}{t('wan_yuan',L)}")
        c2.metric(_t('亏损概率','Loss Probability'),f"{mc_res['p_loss']}%")
        risk_lbl=mc_res['risk_level_zh'] if L=='zh' else mc_res['risk_level_en']
        c3.metric(_t('风险等级','Risk Level'),risk_lbl)
        c4.metric(_t('ROI均值','ROI Mean'),f"{mc_res['roi_mean']:.0f}%",
                  f"[{mc_res['roi_ci_lower']:.0f}%, {mc_res['roi_ci_upper']:.0f}%]")

        st.divider()
        c1,c2=st.columns(2)
        with c1:
            st.write(f"**{_t('NPV概率分布','NPV Probability Distribution')}**")
            fig=go.Figure(data=[go.Histogram(x=mc_res['npv_samples'],nbinsx=50,
                marker_color='rgba(46,182,80,0.7)',marker_line_color='#1B4A2A',marker_line_width=1)])
            fig.add_vline(x=0,line_dash='dash',line_color='red',line_width=2,
                          annotation_text=_t('盈亏平衡','Break-even'),annotation_position='top left')
            fig.add_vline(x=mc_res['npv_p50'],line_dash='dot',line_color='blue',
                          annotation_text='P50',annotation_position='top right')
            fig.update_layout(xaxis_title=f"NPV ({t('wan_yuan',L)})",yaxis_title=_t('频次','Frequency'),height=380)
            st.plotly_chart(fig,use_container_width=True,key='mc_npv_hist')

        with c2:
            st.write(f"**{_t('NPV累积概率曲线(S-Curve)','NPV Cumulative Probability (S-Curve)')}**")
            sorted_npv=np.sort(mc_res['npv_samples'])
            cdf=np.arange(1,len(sorted_npv)+1)/len(sorted_npv)*100
            fig=go.Figure(data=[go.Scatter(x=sorted_npv,y=cdf,mode='lines',line=dict(color='#2E75B6',width=2))])
            fig.add_hline(y=50,line_dash='dot',line_color='gray')
            fig.add_vline(x=0,line_dash='dash',line_color='red')
            fig.update_layout(xaxis_title=f"NPV ({t('wan_yuan',L)})",yaxis_title=_t('累积概率 (%)','Cumulative Prob (%)'),height=380)
            st.plotly_chart(fig,use_container_width=True,key='mc_scurve')

        st.divider()
        st.write(f"**{_t('关键统计指标','Key Statistics')}**")
        stats_data={
            _t('指标','Metric'): ['P10',_t('P50(中位数)','P50 (Median)'),'P90',
                                   _t('90%置信区间','90% CI'),_t('亏损概率','Loss Prob.')],
            _t('NPV(万元)',f'NPV({t("wan_yuan",L)})'): [
                f"{mc_res['npv_p10']:.0f}",f"{mc_res['npv_p50']:.0f}",f"{mc_res['npv_p90']:.0f}",
                f"[{mc_res['npv_ci_lower']:.0f}, {mc_res['npv_ci_upper']:.0f}]",f"{mc_res['p_loss']}%"],
        }
        st.dataframe(pd.DataFrame(stats_data),use_container_width=True,hide_index=True)

        # Tornado chart - input parameter sensitivity
        st.divider()
        st.write(f"**{_t('输入参数分布假设','Input Parameter Distribution Assumptions')}**")
        param_df=[]
        pnames={'gold_price':_t('金价','Gold Price'),'mining_cost':_t('采矿成本','Mining Cost'),
                'grade':_t('品位','Grade')}
        for pk,pv in mc_res['param_distributions'].items():
            draws=np.array(pv['draws'])
            param_df.append({_t('参数','Param'):pnames.get(pk,pk),
                _t('均值','Mean'):f"{pv['mean']:.2f}",_t('变异系数','CV'):f"{pv['cv']*100:.0f}%",
                _t('模拟均值','Sim Mean'):f"{np.mean(draws):.2f}",
                _t('模拟标准差','Sim Std'):f"{np.std(draws):.2f}",_t('单位','Unit'):pv['unit']})
        st.dataframe(pd.DataFrame(param_df),use_container_width=True,hide_index=True)

    # --- TAB 10: SENSITIVITY ANALYSIS ---
    with tabs[10]:
        _t = lambda zh,en: zh if L=='zh' else en
        st.subheader(_t('📈 敏感性分析','📈 Sensitivity Analysis'))

        sa_tab1,sa_tab2=st.tabs([_t('危险度W敏感性','Hazard W Sensitivity'),_t('NPV敏感性','NPV Sensitivity')])

        with sa_tab1:
            st.write(f"**{_t('龙卷风图：各参数对W的影响幅度','Tornado Chart: Parameter Impact on W')}**")
            pname_map={'rqd':'RQD','rock_ucs_roof':_t('顶板UCS','Roof UCS'),'ore_ucs':_t('矿石UCS','Ore UCS'),
                       'depth':_t('埋深','Depth'),'elastic_modulus':_t('弹性模量','Elastic Mod.'),
                       'joint_spacing':_t('节理间距','Joint Spacing'),'thickness':_t('厚度','Thickness')}
            tornado=sa_w['tornado']
            fig=go.Figure()
            for td in tornado:
                name=pname_map.get(td['param_name'],td['param_name'])
                fig.add_trace(go.Bar(y=[name],x=[td['high']-td['base_output']],base=[td['base_output']],
                    orientation='h',marker_color='#E74C3C',name='+30%',showlegend=False,
                    hovertemplate=f"{name}: {td['high']:.4f}"))
                fig.add_trace(go.Bar(y=[name],x=[td['low']-td['base_output']],base=[td['base_output']],
                    orientation='h',marker_color='#3498DB',name='-30%',showlegend=False,
                    hovertemplate=f"{name}: {td['low']:.4f}"))
            fig.add_vline(x=w['W'],line_dash='dash',line_color='black',line_width=2)
            fig.update_layout(barmode='overlay',height=350,xaxis_title='W',
                              title=_t('各参数±30%变化对W的影响','Impact of ±30% Parameter Change on W'))
            st.plotly_chart(fig,use_container_width=True,key='tornado_w')

            st.divider()
            st.write(f"**{_t('蛛网图：参数变化趋势','Spider Chart: Parameter Variation Trends')}**")
            fig2=go.Figure()
            for s in sa_w['sensitivities']:
                name=pname_map.get(s['param_name'],s['param_name'])
                pcts=[r['variation_pct'] for r in s['results']]
                vals=[r['output_value'] for r in s['results']]
                fig2.add_trace(go.Scatter(x=pcts,y=vals,mode='lines+markers',name=name))
            fig2.update_layout(xaxis_title=_t('参数变化 (%)','Parameter Change (%)'),
                               yaxis_title='W',height=400,
                               title=_t('关键参数对W的影响趋势','Key Parameter Impact Trends on W'))
            st.plotly_chart(fig2,use_container_width=True,key='spider_w')

        with sa_tab2:
            st.write(f"**{_t('龙卷风图：各参数对NPV的影响幅度','Tornado Chart: Parameter Impact on NPV')}**")
            npv_pname={'gold_price':_t('金价','Gold Price'),'grade':_t('品位','Grade'),
                       'recovery_rate':_t('回收率','Recovery'),'mining_cost':_t('采矿成本','Mining Cost'),
                       'processing_cost':_t('选矿成本','Processing'),'backfill_cost':_t('充填成本','Backfill Cost')}
            tornado_n=sa_npv['tornado']
            fig=go.Figure()
            for td in tornado_n:
                name=npv_pname.get(td['param_name'],td['param_name'])
                fig.add_trace(go.Bar(y=[name],x=[td['high']-td['base_output']],base=[td['base_output']],
                    orientation='h',marker_color='#E74C3C',showlegend=False))
                fig.add_trace(go.Bar(y=[name],x=[td['low']-td['base_output']],base=[td['base_output']],
                    orientation='h',marker_color='#3498DB',showlegend=False))
            fig.add_vline(x=econ['npv_wan'],line_dash='dash',line_color='black',line_width=2)
            fig.update_layout(barmode='overlay',height=350,xaxis_title=f"NPV ({t('wan_yuan',L)})",
                              title=_t('各参数±30%变化对NPV的影响','Impact of ±30% Change on NPV'))
            st.plotly_chart(fig,use_container_width=True,key='tornado_npv')

            st.divider()
            st.write(f"**{_t('蛛网图：参数变化趋势','Spider Chart: Parameter Variation Trends')}**")
            fig2=go.Figure()
            for s in sa_npv['sensitivities']:
                name=npv_pname.get(s['param_name'],s['param_name'])
                pcts=[r['variation_pct'] for r in s['results']]
                vals=[r['output_value'] for r in s['results']]
                fig2.add_trace(go.Scatter(x=pcts,y=vals,mode='lines+markers',name=name))
            fig2.update_layout(xaxis_title=_t('参数变化 (%)','Parameter Change (%)'),
                               yaxis_title=f"NPV ({t('wan_yuan',L)})",height=400,
                               title=_t('关键参数对NPV的影响趋势','Key Parameter Impact Trends on NPV'))
            st.plotly_chart(fig2,use_container_width=True,key='spider_npv')

    # --- TAB 11: REPORT EXPORT ---
    with tabs[11]:
        _t = lambda zh,en: zh if L=='zh' else en
        st.subheader(_t('📄 综合决策报告导出','📄 Decision Report Export'))
        st.write(_t('点击下方按钮下载Excel格式的综合决策报告，包含所有评价结果、推荐方案和风险分析。',
                     'Click the button below to download the Excel decision report with all evaluation results, recommendations and risk analysis.'))

        report_bytes=generate_excel_report(mine_name,L,w,rvi,fi,meth,mat,econ,cloud_res,mc_res,fus,knn)
        timestamp=datetime.now().strftime('%Y%m%d_%H%M')
        fname=f"{mine_name}_{_t('决策报告','Report')}_{timestamp}.xlsx"

        st.download_button(
            label=_t('📥 下载Excel决策报告','📥 Download Excel Report'),
            data=report_bytes,
            file_name=fname,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            type='primary',
            use_container_width=True
        )

        st.divider()
        st.write(_t('**报告包含以下内容：**','**Report includes:**'))
        contents=[
            _t('✅ 综合总览（W/RVI/FI/推荐方案/经济指标）','✅ Overview (W/RVI/FI/Recommendations/Economics)'),
            _t('✅ 地质危险度W₁评分明细（13个因素）','✅ Geological Hazard W₁ Score Details (13 factors)'),
            _t('✅ 开采危险度W₂评分明细（9个因素）','✅ Mining Hazard W₂ Score Details (9 factors)'),
            _t('✅ 充填方法排名（7种方法完整评分）','✅ Backfill Method Ranking (7 methods)'),
            _t('✅ 充填材料选型（含被排除材料及原因）','✅ Material Selection (with filtered materials & reasons)'),
            _t('✅ 经济效益分析（NPV/ROI/回收期）','✅ Economic Analysis (NPV/ROI/Payback)'),
            _t('✅ 云模型不确定性结果','✅ Cloud Model Uncertainty Results'),
            _t('✅ Monte Carlo风险模拟结果','✅ Monte Carlo Risk Simulation Results'),
            _t('✅ 双路径融合对比','✅ Dual-Path Fusion Comparison'),
            _t('✅ KNN最相似历史案例','✅ KNN Most Similar Historical Cases'),
        ]
        for c in contents:
            st.write(c)

else:
    st.info(t('welcome_msg',L)); st.divider(); st.subheader(t('system_intro',L))
    c1,c2,c3=st.columns(3)
    with c1: st.markdown(f"### 🔴 {t('eval_layer',L)}"); st.write(t('eval_desc',L))
    with c2: st.markdown(f"### 🏗️ {t('decision_layer',L)}"); st.write(t('decision_desc',L))
    with c3: st.markdown(f"### 💰 {t('output_layer',L)}"); st.write(t('output_desc',L))
    st.divider(); st.caption(t('copyright',L))
