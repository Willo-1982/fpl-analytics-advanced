
ATTACK_MULTIPLIER={1:1.15,2:1.10,3:1.00,4:0.90,5:0.82}
CS_PROB_BY_DIFF={1:0.55,2:0.45,3:0.30,4:0.18,5:0.10}
POSITION_MAP={1:"GK",2:"DEF",3:"MID",4:"FWD"}

def cap01(x): return max(0.0,min(1.0,x))
def expected_minutes(mins, completed, chance):
    base=1.0 if completed<=0 else cap01((mins/(completed*90.0)) if completed>0 else 1.0)
    if chance is not None: base*=cap01(chance/100.0)
    return 90.0*base
def appearance_points(m): return 2.0 if m>=60 else 1.0
def get_attack_multiplier(d): return ATTACK_MULTIPLIER.get(int(d),1.0)
def get_cs_prob(d): return CS_PROB_BY_DIFF.get(int(d),0.30)
def compute_fixture_ep(row,pos):
    scale=row['expected_minutes']/90.0; atk=row['attack_mult']
    ep_att=(row['xg_per90']*scale)*4.0 + (row['xa_per90']*scale)*3.0
    ep_att*=atk
    ep_cs=row['cs_prob']*4.0 if pos in ("DEF","GK") else 0.0
    return ep_att + ep_cs + appearance_points(row['expected_minutes'])
