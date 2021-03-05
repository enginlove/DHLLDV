'''
Created on Mar 3, 2015

@author: rcriii
'''

from . import stratified
from . import heterogeneous
from . import homogeneous
from .DHLLDV_constants import gravity, particle_ratio, stk_fine
from math import pi, exp, log10

alpha_xi = 0.5    # alpha in Eqn 8.12-9

use_sf = True        # use these corrections by default, but can be overridden
use_sqrtcx = True


def Cvs_Erhg(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvs, get_dict=False):
    """
    Cvs_Erhg - Calculate the Erhg for the given slurry, using the appropriate model
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvs = insitu volume concentration
    get_dict: if true return the dict with all models.
    """
    Erhg_obj = {'il': homogeneous.fluid_head_loss(vls, Dp, epsilon, nu, rhol),
                'FB': stratified.fb_Erhg(vls, Dp, d, epsilon, nu, rhol, rhos, Cvs),
                'SB':    stratified.Erhg(vls, Dp, d, epsilon, nu, rhol, rhos, Cvs),
                'He': heterogeneous.Erhg(vls, Dp, d, epsilon, nu, rhol, rhos, Cvs, use_sf, use_sqrtcx),
                'Ho':   homogeneous.Erhg(vls, Dp, d, epsilon, nu, rhol, rhos, Cvs),
                }

    if Erhg_obj['FB'] < Erhg_obj['SB']:
        regime = 'FB'
    else:
        regime = 'SB'

    if Erhg_obj[regime] > Erhg_obj['He']:
        regime = 'He'

    if Erhg_obj[regime] < Erhg_obj['Ho']:
        regime = 'Ho'

    Erhg_obj['regime'] = regime

    if get_dict:
        return Erhg_obj
    else:
        return Erhg_obj[Erhg_obj['regime']]


def Cvs_regime(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvs):
    """
    Return the name of the regime for the given slurry and velocity
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvs = insitu volume concentration
    """
    Erhg_obj = Cvs_Erhg(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvs, get_dict=True)
    return {'FB': 'fixed bed',
            'SB': 'sliding bed',
            'He': 'heterogeneous',
            'Ho': 'homogeneous',
            }[Erhg_obj['regime']]


def LDV(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvs, max_steps=10):
    """
    Return the LDV for the given slurry.
    vls: not used, included for consistency sake
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvs = insitu volume concentration
    """
    Rsd = (rhos-rhol)/rhol
    fbot = (2*gravity*Rsd*Dp)**0.5

    # Very Small Particles
    vls = 1.0
    Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
    lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
    FL_vs = 1.4*(nu*Rsd*gravity)**(1./3.)*(8/lambdal)**0.5/fbot # Eqn 8.11-1
    vlsldv = FL_vs*fbot
    steps = 0
    while not (1.00001 >= vls/vlsldv > 0.99999) and steps < max_steps:
        vls = (vls + vlsldv)/2
        Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
        lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
        FL_vs = 1.4*(nu*Rsd*gravity)**(1./3.)*(8/lambdal)**0.5/fbot # Eqn 8.11-1
        vlsldv = FL_vs*fbot
        steps += 1

    # Small Particles
    vls = 4.0
    Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
    lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
    alphap = 3.4 * (1.65/Rsd)**(2./9) # Eqn 8.11-3
    vt = heterogeneous.vt_ruby(d, Rsd, nu)
    Rep = vt*d/nu  # Eqn 4.2-6
    top = 4.7 + 0.41*Rep**0.75
    bottom = 1. + 0.175*Rep**0.75
    beta = top/bottom  # Eqn 4.6-4
    KC = 0.175*(1+beta)
    FL_ss = alphap * (vt*Cvs*(1-Cvs/KC)**beta/(lambdal*fbot))**(1./3) # Eqn 8.11-3
    vlsldv = FL_ss*fbot
    steps = 0
    while not (1.00001 >= vls/vlsldv > 0.99999) and steps < max_steps:
        vls = (vls + vlsldv)/2
        Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
        lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
        FL_ss = alphap * (vt*Cvs*(1-Cvs/KC)**beta/(lambdal*fbot))**(1./3) # Eqn 8.11-3
        vlsldv = FL_ss*fbot
        steps += 1

    FL_s = max(FL_vs, FL_ss)    # Eqn 8.11-4

    # Large particles
    vls=4.3
    if d <= 0.015*Dp:
        Cvr_ldv = 0.0065/(2*gravity*Rsd*Dp) # Eqn 8.11-7
    else:
        Cvr_ldv = 0.053*(d/Dp)**0.5/(2*gravity*Rsd*Dp) # Eqn 8.11-7
    Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
    lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
    FL_r = alphap*((1-Cvs/KC)**beta * Cvs * (stratified.musf*stratified.Cvb*pi/8)**0.5 * Cvr_ldv**0.5/lambdal)**(1./3) # Eqn 8.11-6
    vlsldv = FL_r*fbot
    steps = 0
    while not (1.00001 >= vls/vlsldv > 0.99999) and steps < max_steps:
        vls = (vls + vlsldv)/2
        Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
        lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
        FL_r = alphap*((1-Cvs/KC)**beta * Cvs * (stratified.musf*stratified.Cvb*pi/8)**0.5 * Cvr_ldv**0.5/lambdal)**(1./3) # Eqn 8.11-6
        vlsldv = FL_r*fbot
        steps += 1

    # The Upper limit
    d0 = 0.0005*(1.65/Rsd)**0.5 # Eqn 8.11-8
    drough = 2./1000 # Note: only valid for sand with Rsd=1.65
    if d > drough:
        FL_ul = FL_r
    elif FL_s <= FL_r:
        FL_ul = FL_s
    else:
        FL_ul = FL_s*exp(-1*d/d0) + FL_r*(1-exp(-1*d/d0))   # Eqn 8.11-8

    vls = 2.0
    Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
    lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
    A = -1
    B = vt*(1-Cvs/KC)**beta/stratified.musf
    C = ((8.5**2/lambdal)*(vt/(gravity*d)**0.5)**(10./3)*(nu*gravity)**(2./3))/stratified.musf
    vlsldv = (-1*B - (B**2-4*A*C)**0.5)/(2*A)   # Eqn 8.10-11
    steps = 0
    while not (1.00001 >= vls/vlsldv > 0.99999) and steps < max_steps:
        vls = (vls + vlsldv)/2
        Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
        lambdal = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
        A = -1
        B = vt*(1-Cvs/KC)**beta/stratified.musf
        C = ((8.5**2/lambdal)*(vt/(gravity*d)**0.5)**(10./3)*(nu*gravity)**(2./3))/stratified.musf
        vlsldv = (-1*B - (B**2-4*A*C)**0.5)/(2*A)   # Eqn 8.11-11
        steps += 1
    FL_ll = vlsldv/fbot # Eqn 8.11-12

    FL = max(FL_ul, FL_ll)  # Eqn 8.11-13
    return FL*fbot


def slip_ratio(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvt):
    """
    Return the slip ratio (Xi) for the given slurry.
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvt = transport volume concentration
    """
    if vls == 0.0:
        vls = 0.01
    Rsd = (rhos - rhol)/rhol     # Eqn 8.2-1
    Cvb = stratified.Cvb
    Cvr = Cvt/Cvb
    vt = heterogeneous.vt_ruby(d, Rsd, nu)  # Particle shape factor assumed for sand for now
    CD = (4/3.)*((gravity*Rsd*d)/vt**2)     # Eqn 4.4-6 without the shape factor
    Rep = vt*d/nu       # Eqn 4.2-6
    top = 4.7 + 0.41*Rep**0.75
    bottom = 1. + 0.175*Rep**0.75
    beta = top/bottom   # Eqn 4.6-4
    KC = 0.175*(1+beta)
    vls_ldv = LDV(vls, Dp, d, epsilon, nu, rhol, rhos, Cvt)
    vls_lsdv = stratified.vls_lsdv(Dp,  d, epsilon, nu, rhol, rhos, Cvt)

    Re = homogeneous.pipe_reynolds_number(vls, Dp, nu)
    lambda_l = homogeneous.swamee_jain_ff(Re, Dp, epsilon)
    Xi_HeHo = 8.5*(1/lambda_l)*(vt/(gravity*d)**0.5)**5/3*((nu*gravity)**(1/3)/vls)*(vt/vls) # Eqn 8.12-1

    alpha = 0.58*Cvr**-0.42
    ex1 = -(0.83 + stratified.musf/4 + (Cvr - 0.5 - 0.075*Dp)**2 + (0.025*Dp))
    ex2 = Dp**0.025*(vls_ldv/vls_lsdv)**alpha*Cvr**0.65*(Rsd/1.585)**0.1
    Xi_ldv = (1-Cvr) * exp(ex1*ex2)  # Eqn 8.12-2
    Xi_aldv = Xi_ldv * (vls_ldv/vls)**4
    vls_t = (5 * exp(ex1 * ex2)) ** 0.25 * vls_ldv  # Eqn 8.12-7

    Kldv = 1/(1 - Xi_ldv)       # Eqn 7.9-14
    Xi_fb = 1-((Cvt*vls_ldv)/(Cvb-Kldv*Cvt)*(vls_ldv-vls)+Kldv*Cvt*vls_ldv) # Eqn 8.12-3

    ex2 = Dp ** 0.025 * (vls / vls_lsdv) ** alpha * Cvr ** 0.65 * (Rsd / 1.585) ** 0.1
    Xi_3LM = (1 - Cvr) * exp(ex1 * ex2)  # Eqn 8.12-4

    if Xi_fb < Xi_aldv:     # Eqn 8.12-5
        Xi_th = Xi_fb
    elif Xi_HeHo > Xi_aldv:
        Xi_th = Xi_HeHo
    else:
        Xi_th = Xi_aldv

    if vls < vls_t:
        Xi_t = (1 - Cvr) * (1 - (4. / 5.) * (vls / vls_t))  # Eqn 8.12-8
        Xi_SBHeHo = Xi_th*(1-(vls/vls_t)**alpha_xi) + Xi_t*(vls/vls_t)**alpha_xi # Eqn 8.12-9
    else:
        Xi_SBHeHo = Xi_th # Eqn 8.12-9
    Xi_SBHeHo = max(Xi_SBHeHo, Xi_3LM) # Eqn 8.12-9

    f = 4./3. - (1./3.)*(d/Dp)/particle_ratio # Eqn 8.12-10 TODO: update with dynamic particle ratio in section 7.7.5
    f = min(max(f, 0), 1)
    Xi_SF = Xi_SBHeHo * f + Xi_3LM*(1-f)    # Eqn 8.12-11
    return Xi_SF

def Cvs_from_Cvt(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvt):
    """
    Cvs_from_Cvt - Calculate the Cvs for the given Cvt
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvt = transported volume concentration
    get_dict: if true return the dict with all models.
    """
    Xi = slip_ratio(vls, Dp, d, epsilon, nu, rhol, rhos, Cvt)
    return (1/(1-Xi)) * Cvt # Eqn 8.12-12


def Cvt_Erhg(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvt, get_dict=False):
    """
    Cvt_Erhg - Calculate the Erhg for the given Cvt, using the appropriate model
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvt = transported volume concentration
    get_dict: if true return the dict with all models.
    """
    Cvs = Cvs_from_Cvt(vls, Dp, d, epsilon, nu, rhol, rhos, Cvt)
    Xi = slip_ratio(vls, Dp, d, epsilon, nu, rhol, rhos, Cvt)
    Erhg_obj = Cvs_Erhg(vls, Dp, d, epsilon, nu, rhol, rhos, Cvs, get_dict=True)
    if Erhg_obj['regime'] == "FB":
        # Use min of SB, He if in fixed bed region
        if Erhg_obj["SB"] < Erhg_obj["He"]:
            Erhg_obj['regime'] = "SB"
        else:
            Erhg_obj['regime'] = "He"
    if get_dict:
        return {regime: e*1/(1-Xi) for regime, e in Erhg_obj.items()} # Eqn 8.12-12
    else:
        return Erhg_obj[Erhg_obj['regime']]*1/(1-Xi) # Eqn 8.12-12


def Cvt_regime(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvt):
    """
    Return the name of the regime for the given slurry and velocity in the Cvt case
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    d = Particle diameter (m)
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvs = insitu volume concentration
    """
    Erhg_obj = Cvt_Erhg(vls, Dp,  d, epsilon, nu, rhol, rhos, Cvt, get_dict=True)
    return {'FB': 'fixed bed',
            'SB': 'sliding bed',
            'He': 'heterogeneous',
            'Ho': 'homogeneous',
            }[Erhg_obj['regime']]

def add_dlim_to_GSD(GSD, Dp, nu, rhol, rhos):
    """
    Return the name of the regime for the given slurry and velocity in the Cvt case
    GSD: A dict with a grain size distribution in the form {% Passing:d,...}, must have len>1
    Dp = Pipe diameter (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    """

    dlim = (stk_fine*9*rhol*nu*Dp / (rhos*7.5*Dp))**0.5 # Eqn 8.15-2
    if len(GSD)<2:
        GSD[dlim] = 0
        return GSD
    fracs = sorted(GSD.keys())
    sizes = [GSD[p] for p in fracs]
    lowslope = (fracs[1] - fracs[0]) / (log10(sizes[1]) - log10(sizes[0]))
    GSD[dlim] = fracs[0] - (log10(sizes[0])-log10(dlim))*lowslope
    return GSD


def calc_GSD_fractions(GSD, n=10):
    """
    Break the given Grain Size Distribution into n fractions, and add % passing d_lim.
    GSD: A dict with a grain size distribution in the form {% Passing:d,...}, must have len>1
    Cvs = Spatial volume concentration
    n: number of fractions (including d=0.057)
    Scheme:
    Find fraction <.057
    separate GSD into n even pieces, _add_ these to the GSD dict
    Interpolate between the given fractions, assuming log scale on the x-axis
    Note that at the top and bottom the slope is halved
    """
    if len(GSD) < 2:
        return GSD
    fracs = sorted(GSD.keys())
    sizes = [GSD[p] for p in fracs]

    # The n fractions - note you could end up with n + len(GSD) + 1
    fracs = sorted(GSD.keys())
    sizes = [GSD[p] for p in fracs]
    f_index = 1
    for i in range(n-1):
        this_frac = float((i+1))/n
        if this_frac > fracs[f_index]:
            f_index = min(f_index+1, len(fracs)-1)
        slope = (fracs[f_index] - fracs[f_index-1])/(log10(sizes[f_index])-log10(sizes[f_index-1]))
        if this_frac > fracs[-1]:
            slope = slope/2  # halve the slope above the largest given size
            log_size = (this_frac - fracs[f_index])/slope + log10(sizes[f_index])
        else:
            log_size = (this_frac - fracs[f_index-1])/slope + log10(sizes[f_index-1])
        this_size = 10**log_size
        GSD[this_frac] = this_size
    return GSD


def Cvs_Erhg_graded(vls, Dp,  GSD, epsilon, nu, rhol, rhos, Cvs, get_dict=False):
    """
    Cvs_Erhg_graded - Calculate the Erhg for the given slurry, using the appropriate model
    vls = average line speed (velocity, m/sec)
    Dp = Pipe diameter (m)
    GSD = Particle size distribution dict: {f1:d1, f2:d2, ...}
          assume GSD is already in proper fractions
    epsilon = absolute pipe roughness (m)
    nu = fluid kinematic viscosity in m2/sec
    rhol = density of the fluid (ton/m3)
    rhos = particle density (ton/m3)
    Cvs = insitu volume concentration
    get_dict: Does nothing for now
    """
    # first adjust the liquid density
    GSD = calc_GSD_fractions(GSD, n=1)  # This ensures there is a fraction for the ultra_fines
    fracs = sorted(GSD.keys())
    sizes = [GSD[p] for p in fracs]
    Cvs_uf = Cvs*fracs[0]
    Cvs_c = Cvs - Cvs_uf
    mul = nu * 1000 * rhol
    mu_uf = mul * (1 + 2.5*Cvs_uf + 10.05*Cvs_uf**2 + 0.00273*exp(16.6*Cvs_uf))
    rho_uf = (rhol*(1-Cvs_uf-Cvs_c) + rhos*Cvs_uf)/(1-Cvs_c)
    nu_uf = mu_uf/(1000*rho_uf)
    Rsd_uf = (rhos-rho_uf)/rho_uf

    # The fractions represented by each GSD_frac
    fracs_rep = [fracs[0]]
    for i in range(1, len(fracs)):
        if i == 1:  # First fraction after uf
            fhere = (fracs[i]-fracs[i-1]) + (fracs[i+1]-fracs[i])/2
        elif i == len(fracs)-1:  # last fraction
            fhere = (fracs[i]-fracs[i-1])/2 + (1. - fracs[i])
        else:  # intermediate fractions
            fhere = (fracs[i] - fracs[i - 1])/2 + (fracs[i + 1] - fracs[i])/2
        fracs_rep.append(fhere)

    # the Cvs for each fraction
    Cvs_fracs = [Cvs_uf]
    for f in fracs_rep:
        Cvs_fracs.append(Cvs * f)

    # The im for each fraction and total
    im_tot = 0
    for i in range(1, len(sizes)):
        d_i = sizes[i]
        Cvs_i = Cvs_fracs[i]
        Erhg_i = Cvs_Erhg(vls, Dp, d_i, epsilon, nu_uf, rho_uf, rhos, Cvs, False)
        il_uf = homogeneous.fluid_head_loss(vls, Dp, epsilon, nu_uf, rho_uf)
        im_i = Erhg_i * Rsd_uf * Cvs + il_uf
        im_tot += im_i * Cvs_i / Cvs_c

    il = homogeneous.fluid_head_loss(vls, Dp, epsilon, nu, rhol)
    Rsd = (rhos - rhol) / rhol
    return (im_tot - il) / (Rsd * Cvs)


if __name__ == '__main__':
    pass
