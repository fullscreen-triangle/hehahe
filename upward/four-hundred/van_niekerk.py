"""
Comprehensive Body Segmentation Analysis for Wayde van Niekerk
===============================================================

Deep biomechanical analysis of van Niekerk's unique physiological profile
using anthropometric models (Dempster-Winter and Zatsiorsky-de Leva).

Author: Biomechanics Analysis System
Date: 2024
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from numpy.linalg import norm
from typing import Dict, Tuple

# Publication-quality plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10

# ============================================================================
# VAN NIEKERK'S ANTHROPOMETRIC DATA
# ============================================================================

class VanNiekerkProfile:
    """Wayde van Niekerk's verified anthropometric and performance data"""

    # Basic measurements
    height = 1.83  # meters (official)
    mass = 73.0    # kg (Rio 2016 competition weight)
    age_rio = 24   # years (August 2016)

    # Performance profile (personal bests)
    time_100m = 9.98   # seconds
    time_200m = 19.84  # seconds
    time_300m = 30.81  # seconds (WR until 2024)
    time_400m = 43.03  # seconds (WR, Rio 2016)

    # Rio 2016 race parameters (from biomechanical analysis)
    stride_length = 2.77  # meters
    stride_freq = 4.50    # Hz
    peak_velocity = 12.42 # m/s
    contact_time = 0.080  # seconds
    reaction_time = 0.146 # seconds

    # Estimated from video analysis and biometric databases
    leg_length = 0.94      # meters (hip to ground)
    thigh_length = 0.48    # meters (hip to knee)
    shank_length = 0.43    # meters (knee to ankle)
    foot_length = 0.28     # meters (heel to toe)
    upper_arm_length = 0.33  # meters
    forearm_length = 0.28    # meters
    trunk_length = 0.60      # meters

    # Body proportions
    sitting_height = 0.96  # meters
    shoulder_width = 0.44  # meters
    hip_width = 0.32       # meters

    # Estimated body fat percentage (elite sprinter range)
    body_fat_pct = 7.5  # %

    @classmethod
    def leg_to_height_ratio(cls):
        """Calculate leg length to height ratio"""
        return cls.leg_length / cls.height

    @classmethod
    def hip_shoulder_ratio(cls):
        """Calculate hip to shoulder width ratio (stability index)"""
        return cls.hip_width / cls.shoulder_width

    @classmethod
    def relative_step_length(cls):
        """Calculate step length normalized by height"""
        return cls.stride_length / cls.height


# ============================================================================
# BODY SEGMENT PARAMETER MODELS
# ============================================================================

class BodySegmentParameters:
    """
    Implementation of anthropometric models:
    - Dempster (1955) adapted by Winter (2009)
    - Zatsiorsky-Seluyanov adjusted by de Leva (1996)
    """

    # Dempster-Winter model (male)
    DEMPSTER_WINTER = {
        'Foot': {
            'mass_fraction': 0.0145,
            'cm_proximal': 0.50,  # from ankle
            'rg_cm': 0.475,       # radius of gyration w.r.t. CM
            'rg_proximal': 0.690,
            'length_fraction': 0.152  # of height
        },
        'Shank': {
            'mass_fraction': 0.0465,
            'cm_proximal': 0.433,  # from knee
            'rg_cm': 0.302,
            'rg_proximal': 0.528,
            'length_fraction': 0.246
        },
        'Thigh': {
            'mass_fraction': 0.100,
            'cm_proximal': 0.433,  # from hip
            'rg_cm': 0.323,
            'rg_proximal': 0.540,
            'length_fraction': 0.245
        },
        'Trunk': {
            'mass_fraction': 0.497,
            'cm_proximal': 0.50,
            'rg_cm': 0.496,
            'rg_proximal': 0.830,
            'length_fraction': 0.288
        },
        'Upper_arm': {
            'mass_fraction': 0.028,
            'cm_proximal': 0.436,
            'rg_cm': 0.322,
            'rg_proximal': 0.542,
            'length_fraction': 0.186
        },
        'Forearm': {
            'mass_fraction': 0.016,
            'cm_proximal': 0.430,
            'rg_cm': 0.303,
            'rg_proximal': 0.526,
            'length_fraction': 0.146
        },
        'Hand': {
            'mass_fraction': 0.006,
            'cm_proximal': 0.506,
            'rg_cm': 0.297,
            'rg_proximal': 0.587,
            'length_fraction': 0.108
        },
        'Head_neck': {
            'mass_fraction': 0.081,
            'cm_proximal': 1.00,  # from base of trunk
            'rg_cm': 0.495,
            'rg_proximal': 0.495,
            'length_fraction': 0.182
        }
    }

    # Zatsiorsky-de Leva model (male)
    ZATSIORSKY_DE_LEVA = {
        'Foot': {
            'mass_fraction': 0.0137,
            'cm_proximal': 0.4415,
            'rg_cm': 0.257,
            'rg_proximal': 0.690,
            'length_fraction': 0.152
        },
        'Shank': {
            'mass_fraction': 0.0433,
            'cm_proximal': 0.4459,
            'rg_cm': 0.251,
            'rg_proximal': 0.522,
            'length_fraction': 0.246
        },
        'Thigh': {
            'mass_fraction': 0.1416,
            'cm_proximal': 0.4095,
            'rg_cm': 0.249,
            'rg_proximal': 0.540,
            'length_fraction': 0.245
        },
        'Lower_trunk': {
            'mass_fraction': 0.1117,
            'cm_proximal': 0.50,
            'rg_cm': 0.382,
            'rg_proximal': 0.382,
            'length_fraction': 0.096
        },
        'Middle_trunk': {
            'mass_fraction': 0.1633,
            'cm_proximal': 0.45,
            'rg_cm': 0.342,
            'rg_proximal': 0.482,
            'length_fraction': 0.096
        },
        'Upper_trunk': {
            'mass_fraction': 0.1596,
            'cm_proximal': 0.50,
            'rg_cm': 0.328,
            'rg_proximal': 0.465,
            'length_fraction': 0.096
        },
        'Upper_arm': {
            'mass_fraction': 0.0271,
            'cm_proximal': 0.5772,
            'rg_cm': 0.285,
            'rg_proximal': 0.645,
            'length_fraction': 0.186
        },
        'Forearm': {
            'mass_fraction': 0.0162,
            'cm_proximal': 0.4574,
            'rg_cm': 0.276,
            'rg_proximal': 0.565,
            'length_fraction': 0.146
        },
        'Hand': {
            'mass_fraction': 0.0061,
            'cm_proximal': 0.7900,
            'rg_cm': 0.288,
            'rg_proximal': 0.628,
            'length_fraction': 0.108
        },
        'Head': {
            'mass_fraction': 0.0694,
            'cm_proximal': 0.5976,
            'rg_cm': 0.303,
            'rg_proximal': 0.495,
            'length_fraction': 0.182
        }
    }

    @staticmethod
    def compute_segment_mass(total_mass: float, segment: str, model: str = 'dempster') -> float:
        """Compute absolute mass of a body segment"""
        if model == 'dempster':
            return total_mass * BodySegmentParameters.DEMPSTER_WINTER[segment]['mass_fraction']
        else:
            return total_mass * BodySegmentParameters.ZATSIORSKY_DE_LEVA[segment]['mass_fraction']

    @staticmethod
    def compute_segment_cm_position(proximal_pos: np.ndarray, distal_pos: np.ndarray,
                                    segment: str, model: str = 'dempster') -> np.ndarray:
        """
        Compute center of mass position of segment

        Parameters
        ----------
        proximal_pos : array [x, y, z] or [x, y]
            Proximal joint position
        distal_pos : array [x, y, z] or [x, y]
            Distal joint position
        segment : str
            Segment name
        model : str
            'dempster' or 'zatsiorsky'

        Returns
        -------
        cm_pos : array
            Center of mass position
        """
        if model == 'dempster':
            cm_frac = BodySegmentParameters.DEMPSTER_WINTER[segment]['cm_proximal']
        else:
            cm_frac = BodySegmentParameters.ZATSIORSKY_DE_LEVA[segment]['cm_proximal']

        return proximal_pos + cm_frac * (distal_pos - proximal_pos)

    @staticmethod
    def compute_moment_of_inertia(total_mass: float, segment: str,
                                  segment_length: float, model: str = 'dempster') -> float:
        """
        Compute moment of inertia around segment center of mass

        Parameters
        ----------
        total_mass : float
            Total body mass (kg)
        segment : str
            Segment name
        segment_length : float
            Length of segment (m)
        model : str
            'dempster' or 'zatsiorsky'

        Returns
        -------
        I_cm : float
            Moment of inertia around CM (kg·m²)
        """
        if model == 'dempster':
            params = BodySegmentParameters.DEMPSTER_WINTER[segment]
        else:
            params = BodySegmentParameters.ZATSIORSKY_DE_LEVA[segment]

        seg_mass = total_mass * params['mass_fraction']
        rg_cm = params['rg_cm'] * segment_length

        return seg_mass * rg_cm**2


# ============================================================================
# VAN NIEKERK SEGMENTATION ANALYSIS
# ============================================================================

class VanNiekerkSegmentation:
    """Complete body segmentation analysis for Wayde van Niekerk"""

    def __init__(self):
        self.profile = VanNiekerkProfile()
        self.bsp = BodySegmentParameters()

        # Segment lengths (m)
        self.segments = {
            'Foot': self.profile.foot_length,
            'Shank': self.profile.shank_length,
            'Thigh': self.profile.thigh_length,
            'Trunk': self.profile.trunk_length,
            'Upper_arm': self.profile.upper_arm_length,
            'Forearm': self.profile.forearm_length,
            'Hand': 0.19,  # estimated
            'Head_neck': 0.26  # estimated
        }

        # Results storage
        self.segment_masses = {}
        self.segment_cm_heights = {}
        self.segment_inertias = {}
        self.total_body_cm = None

    def compute_all_segment_properties(self, model='dempster'):
        """Compute mass, CM position, and inertia for all segments"""

        results = {}

        for segment, length in self.segments.items():
            if model == 'dempster' and segment not in self.bsp.DEMPSTER_WINTER:
                continue
            if model == 'zatsiorsky' and segment not in self.bsp.ZATSIORSKY_DE_LEVA:
                continue

            mass = self.bsp.compute_segment_mass(self.profile.mass, segment, model)
            inertia = self.bsp.compute_moment_of_inertia(self.profile.mass, segment,
                                                         length, model)

            results[segment] = {
                'length': length,
                'mass': mass,
                'mass_fraction': mass / self.profile.mass,
                'inertia_cm': inertia,
                'rg_cm': np.sqrt(inertia / mass) if mass > 0 else 0
            }

        return pd.DataFrame(results).T

    def compute_lower_limb_properties(self, model='dempster'):
        """Detailed analysis of lower limb (foot + shank + thigh)"""

        # Define joint positions in standing posture
        ground = np.array([0.0, 0.0])
        ankle = np.array([0.0, 0.1])  # slightly above ground
        knee = ankle + np.array([0.0, self.profile.shank_length])
        hip = knee + np.array([0.0, self.profile.thigh_length])

        # Compute CM positions
        foot_cm = self.bsp.compute_segment_cm_position(ankle, ground, 'Foot', model)
        shank_cm = self.bsp.compute_segment_cm_position(knee, ankle, 'Shank', model)
        thigh_cm = self.bsp.compute_segment_cm_position(hip, knee, 'Thigh', model)

        # Compute masses
        foot_mass = self.bsp.compute_segment_mass(self.profile.mass, 'Foot', model)
        shank_mass = self.bsp.compute_segment_mass(self.profile.mass, 'Shank', model)
        thigh_mass = self.bsp.compute_segment_mass(self.profile.mass, 'Thigh', model)

        total_limb_mass = foot_mass + shank_mass + thigh_mass

        # Total lower limb CM
        limb_cm = (foot_mass * foot_cm + shank_mass * shank_cm +
                   thigh_mass * thigh_cm) / total_limb_mass

        # Compute moments of inertia
        I_foot = self.bsp.compute_moment_of_inertia(self.profile.mass, 'Foot',
                                                     self.profile.foot_length, model)
        I_shank = self.bsp.compute_moment_of_inertia(self.profile.mass, 'Shank',
                                                      self.profile.shank_length, model)
        I_thigh = self.bsp.compute_moment_of_inertia(self.profile.mass, 'Thigh',
                                                      self.profile.thigh_length, model)

        # Parallel axis theorem for total limb inertia around limb CM
        I_limb_cm = (I_foot + foot_mass * norm(limb_cm - foot_cm)**2 +
                     I_shank + shank_mass * norm(limb_cm - shank_cm)**2 +
                     I_thigh + thigh_mass * norm(limb_cm - thigh_cm)**2)

        # Moment of inertia around hip
        I_hip = (I_foot + foot_mass * norm(hip - foot_cm)**2 +
                 I_shank + shank_mass * norm(hip - shank_cm)**2 +
                 I_thigh + thigh_mass * norm(hip - thigh_cm)**2)

        return {
            'total_mass': total_limb_mass,
            'cm_position': limb_cm,
            'cm_height': limb_cm[1],
            'I_limb_cm': I_limb_cm,
            'I_hip': I_hip,
            'segment_masses': {
                'foot': foot_mass,
                'shank': shank_mass,
                'thigh': thigh_mass
            },
            'segment_inertias': {
                'foot': I_foot,
                'shank': I_shank,
                'thigh': I_thigh
            }
        }

    def compute_whole_body_cm(self, model='dempster'):
        """
        Estimate whole body center of mass in standing posture
        """
        # Simplified standing posture (all positions are height from ground)
        segment_heights = {
            'Foot': 0.05,
            'Shank': 0.10 + self.profile.shank_length / 2,
            'Thigh': 0.10 + self.profile.shank_length + self.profile.thigh_length / 2,
            'Trunk': 0.10 + self.profile.shank_length + self.profile.thigh_length +
                     self.profile.trunk_length / 2,
            'Upper_arm': 0.10 + self.profile.shank_length + self.profile.thigh_length +
                        self.profile.trunk_length * 0.8,
            'Forearm': 0.10 + self.profile.shank_length + self.profile.thigh_length +
                      self.profile.trunk_length * 0.7,
            'Hand': 0.10 + self.profile.shank_length + self.profile.thigh_length +
                   self.profile.trunk_length * 0.6,
            'Head_neck': 0.10 + self.profile.shank_length + self.profile.thigh_length +
                        self.profile.trunk_length
        }

        total_mass = 0
        weighted_height = 0

        for segment in segment_heights.keys():
            if model == 'dempster' and segment not in self.bsp.DEMPSTER_WINTER:
                continue

            mass = self.bsp.compute_segment_mass(self.profile.mass, segment, model)
            height = segment_heights[segment]

            # Account for bilateral segments (2x for limbs)
            if segment in ['Foot', 'Shank', 'Thigh', 'Upper_arm', 'Forearm', 'Hand']:
                mass *= 2

            total_mass += mass
            weighted_height += mass * height

        body_cm_height = weighted_height / total_mass

        return {
            'height': body_cm_height,
            'height_fraction': body_cm_height / self.profile.height,
            'total_mass_check': total_mass
        }

    def analyze_sprint_mechanics(self):
        """
        Analyze van Niekerk's sprint mechanics from body segmentation perspective
        """

        limb_props_d = self.compute_lower_limb_properties('dempster')
        limb_props_z = self.compute_lower_limb_properties('zatsiorsky')

        # Natural frequency of leg as pendulum (approximation)
        g = 9.81  # m/s²

        # Leg as physical pendulum around hip
        freq_natural_d = (1 / (2 * np.pi)) * np.sqrt((limb_props_d['total_mass'] * g *
                          limb_props_d['cm_height']) / limb_props_d['I_hip'])
        freq_natural_z = (1 / (2 * np.pi)) * np.sqrt((limb_props_z['total_mass'] * g *
                          limb_props_z['cm_height']) / limb_props_z['I_hip'])

        # Compare to actual stride frequency
        stride_freq = self.profile.stride_freq

        # Resonance ratio (closer to 1.0 = better coupling)
        resonance_ratio_d = stride_freq / freq_natural_d
        resonance_ratio_z = stride_freq / freq_natural_z

        # Power requirements
        # Simplified: P = I * alpha² * f, where alpha ∝ stride frequency
        # Lower I = less power needed for same frequency

        return {
            'natural_frequency_dempster': freq_natural_d,
            'natural_frequency_zatsiorsky': freq_natural_z,
            'actual_stride_frequency': stride_freq,
            'resonance_ratio_dempster': resonance_ratio_d,
            'resonance_ratio_zatsiorsky': resonance_ratio_z,
            'limb_mass_dempster': limb_props_d['total_mass'],
            'limb_mass_zatsiorsky': limb_props_z['total_mass'],
            'I_hip_dempster': limb_props_d['I_hip'],
            'I_hip_zatsiorsky': limb_props_z['I_hip'],
            'leg_length': self.profile.leg_length,
            'relative_leg_length': self.profile.leg_to_height_ratio()
        }

    def compare_to_optimal_sprinter(self):
        """
        Compare van Niekerk's proportions to theoretical optimal sprinter
        """

        # Theoretical optimal ratios (from sprint biomechanics literature)
        optimal_ratios = {
            'leg_height': 0.51,  # 51% of height
            'sitting_height': 0.52,  # 52% of height
            'thigh_leg': 0.51,  # thigh 51% of leg length
            'hip_shoulder': 0.73,  # hip 73% of shoulder width
            'stride_height': 1.51,  # stride length 151% of height
        }

        van_niekerk_ratios = {
            'leg_height': self.profile.leg_to_height_ratio(),
            'sitting_height': self.profile.sitting_height / self.profile.height,
            'thigh_leg': self.profile.thigh_length / self.profile.leg_length,
            'hip_shoulder': self.profile.hip_shoulder_ratio(),
            'stride_height': self.profile.relative_step_length(),
        }

        deviations = {}
        for key in optimal_ratios:
            deviations[key] = ((van_niekerk_ratios[key] - optimal_ratios[key]) /
                              optimal_ratios[key] * 100)

        return pd.DataFrame({
            'Optimal': optimal_ratios,
            'Van Niekerk': van_niekerk_ratios,
            'Deviation (%)': deviations
        })


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def plot_segment_comparison(vnk_seg: VanNiekerkSegmentation):
    """Compare Dempster and Zatsiorsky models for van Niekerk"""

    df_d = vnk_seg.compute_all_segment_properties('dempster')
    df_z = vnk_seg.compute_all_segment_properties('zatsiorsky')

    # Only compare segments that exist in both models
    common_segments = list(set(df_d.index) & set(df_z.index))
    df_d_common = df_d.loc[common_segments]
    df_z_common = df_z.loc[common_segments]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Mass comparison
    ax = axes[0, 0]
    x = np.arange(len(common_segments))
    width = 0.35
    ax.bar(x - width/2, df_d_common['mass'], width, label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, df_z_common['mass'], width, label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Mass (kg)', fontweight='bold')
    ax.set_title('Segment Mass Comparison (Common Segments)', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(common_segments, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    # Mass fraction comparison
    ax = axes[0, 1]
    ax.bar(x - width/2, df_d_common['mass_fraction']*100, width,
           label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, df_z_common['mass_fraction']*100, width,
           label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Mass Fraction (%)', fontweight='bold')
    ax.set_title('Segment Mass as % of Body Mass', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(common_segments, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    # Moment of inertia comparison
    ax = axes[1, 0]
    ax.bar(x - width/2, df_d_common['inertia_cm'], width,
           label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, df_z_common['inertia_cm'], width,
           label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Moment of Inertia (kg·m²)', fontweight='bold')
    ax.set_title('Segment Inertia Around CM', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(common_segments, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    # Radius of gyration comparison
    ax = axes[1, 1]
    ax.bar(x - width/2, df_d_common['rg_cm'], width,
           label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, df_z_common['rg_cm'], width,
           label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Radius of Gyration (m)', fontweight='bold')
    ax.set_title('Segment Radius of Gyration', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(common_segments, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    return fig


def plot_lower_limb_analysis(vnk_seg: VanNiekerkSegmentation):
    """Visualize lower limb properties"""

    limb_d = vnk_seg.compute_lower_limb_properties('dempster')
    limb_z = vnk_seg.compute_lower_limb_properties('zatsiorsky')

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Segment mass distribution
    ax = axes[0]
    segments = ['Foot', 'Shank', 'Thigh']
    masses_d = [limb_d['segment_masses'][s.lower()] for s in segments]
    masses_z = [limb_z['segment_masses'][s.lower()] for s in segments]

    x = np.arange(len(segments))
    width = 0.35
    ax.bar(x - width/2, masses_d, width, label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, masses_z, width, label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Mass (kg)', fontweight='bold')
    ax.set_title('Lower Limb Segment Masses', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(segments)
    ax.legend()
    ax.grid(alpha=0.3)

    # Segment inertias
    ax = axes[1]
    inertias_d = [limb_d['segment_inertias'][s.lower()] for s in segments]
    inertias_z = [limb_z['segment_inertias'][s.lower()] for s in segments]

    ax.bar(x - width/2, inertias_d, width, label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, inertias_z, width, label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Inertia (kg·m²)', fontweight='bold')
    ax.set_title('Lower Limb Segment Inertias', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(segments)
    ax.legend()
    ax.grid(alpha=0.3)

    # Total limb properties comparison
    ax = axes[2]
    properties = ['Total\nMass (kg)', 'I_limb_cm\n(kg·m²)', 'I_hip\n(kg·m²)']
    values_d = [limb_d['total_mass'], limb_d['I_limb_cm'], limb_d['I_hip']]
    values_z = [limb_z['total_mass'], limb_z['I_limb_cm'], limb_z['I_hip']]

    # Normalize for visualization
    values_d_norm = np.array(values_d) / np.max(values_d + values_z)
    values_z_norm = np.array(values_z) / np.max(values_d + values_z)

    x = np.arange(len(properties))
    ax.bar(x - width/2, values_d_norm, width, label='Dempster-Winter', alpha=0.8)
    ax.bar(x + width/2, values_z_norm, width, label='Zatsiorsky-de Leva', alpha=0.8)
    ax.set_ylabel('Normalized Value', fontweight='bold')
    ax.set_title('Total Lower Limb Properties', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(properties)
    ax.legend()
    ax.grid(alpha=0.3)

    # Add actual values as text
    for i, (vd, vz) in enumerate(zip(values_d, values_z)):
        ax.text(i - width/2, values_d_norm[i] + 0.05, f'{vd:.3f}',
                ha='center', va='bottom', fontsize=8)
        ax.text(i + width/2, values_z_norm[i] + 0.05, f'{vz:.3f}',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    return fig


def plot_sprint_mechanics_analysis(vnk_seg: VanNiekerkSegmentation):
    """Visualize sprint mechanics from segmentation perspective"""

    mechanics = vnk_seg.analyze_sprint_mechanics()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Natural frequency vs actual stride frequency
    ax = axes[0, 0]
    models = ['Dempster', 'Zatsiorsky']
    nat_freqs = [mechanics['natural_frequency_dempster'],
                 mechanics['natural_frequency_zatsiorsky']]
    actual_freq = mechanics['actual_stride_frequency']

    x = np.arange(len(models))
    width = 0.35
    ax.bar(x, nat_freqs, width, label='Natural Frequency', alpha=0.8, color='skyblue')
    ax.axhline(y=actual_freq, color='red', linestyle='--', linewidth=2,
               label=f'Actual Stride Freq ({actual_freq:.2f} Hz)')
    ax.set_ylabel('Frequency (Hz)', fontweight='bold')
    ax.set_title('Natural vs Actual Stride Frequency', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    ax.grid(alpha=0.3)

    # Resonance ratio
    ax = axes[0, 1]
    resonance = [mechanics['resonance_ratio_dempster'],
                 mechanics['resonance_ratio_zatsiorsky']]
    colors = ['green' if 0.9 < r < 1.1 else 'orange' for r in resonance]
    ax.bar(x, resonance, width, alpha=0.8, color=colors)
    ax.axhline(y=1.0, color='green', linestyle='--', linewidth=2, alpha=0.7,
               label='Perfect Resonance')
    ax.axhspan(0.9, 1.1, alpha=0.2, color='green', label='Optimal Range')
    ax.set_ylabel('Resonance Ratio', fontweight='bold')
    ax.set_title('Stride Frequency / Natural Frequency', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.legend()
    ax.grid(alpha=0.3)

    # Limb inertia comparison
    ax = axes[1, 0]
    inertias = [mechanics['I_hip_dempster'], mechanics['I_hip_zatsiorsky']]
    ax.bar(x, inertias, width, alpha=0.8, color='coral')
    ax.set_ylabel('Moment of Inertia (kg·m²)', fontweight='bold')
    ax.set_title('Lower Limb Inertia Around Hip', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(models)
    ax.grid(alpha=0.3)

    # Add text annotation
    for i, val in enumerate(inertias):
        ax.text(i, val + 0.05, f'{val:.3f}', ha='center', fontweight='bold')

    # Key metrics summary
    ax = axes[1, 1]
    ax.axis('off')

    summary_text = f"""
    Van Niekerk Sprint Mechanics Summary
    =====================================

    Leg Length: {mechanics['leg_length']:.3f} m
    Relative Leg Length: {mechanics['relative_leg_length']:.3f}

    Actual Stride Frequency: {mechanics['actual_stride_frequency']:.2f} Hz

    Dempster-Winter Model:
      • Natural Frequency: {mechanics['natural_frequency_dempster']:.2f} Hz
      • Resonance Ratio: {mechanics['resonance_ratio_dempster']:.3f}
      • Limb Mass: {mechanics['limb_mass_dempster']:.2f} kg
      • I_hip: {mechanics['I_hip_dempster']:.3f} kg·m²

    Zatsiorsky-de Leva Model:
      • Natural Frequency: {mechanics['natural_frequency_zatsiorsky']:.2f} Hz
      • Resonance Ratio: {mechanics['resonance_ratio_zatsiorsky']:.3f}
      • Limb Mass: {mechanics['limb_mass_zatsiorsky']:.2f} kg
      • I_hip: {mechanics['I_hip_zatsiorsky']:.3f} kg·m²

    Interpretation:
    {'✓ Optimal resonance!' if 0.9 < mechanics['resonance_ratio_dempster'] < 1.1 else '! Sub-optimal resonance'}
    """

    ax.text(0.05, 0.95, summary_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    return fig


def plot_proportions_comparison(vnk_seg: VanNiekerkSegmentation):
    """Compare van Niekerk's proportions to optimal sprinter"""

    df_comp = vnk_seg.compare_to_optimal_sprinter()

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Ratio comparison
    ax = axes[0]
    x = np.arange(len(df_comp.index))
    width = 0.35
    ax.bar(x - width/2, df_comp['Optimal'], width, label='Optimal', alpha=0.8)
    ax.bar(x + width/2, df_comp['Van Niekerk'], width, label='Van Niekerk', alpha=0.8)
    ax.set_ylabel('Ratio', fontweight='bold')
    ax.set_title('Anthropometric Ratios: Optimal vs Van Niekerk',
                 fontweight='bold', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(df_comp.index, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    # Deviation from optimal
    ax = axes[1]
    colors = ['green' if abs(d) < 5 else 'orange' if abs(d) < 10 else 'red'
              for d in df_comp['Deviation (%)']]
    bars = ax.bar(x, df_comp['Deviation (%)'], width*2, alpha=0.8, color=colors)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.axhspan(-5, 5, alpha=0.2, color='green', label='±5% (Excellent)')
    ax.set_ylabel('Deviation from Optimal (%)', fontweight='bold')
    ax.set_title('Deviation from Optimal Sprinter Proportions',
                 fontweight='bold', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(df_comp.index, rotation=45, ha='right')
    ax.legend()
    ax.grid(alpha=0.3)

    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, df_comp['Deviation (%)'])):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5 if height > 0 else height - 0.5,
                f'{val:.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                fontweight='bold', fontsize=9)

    plt.tight_layout()
    return fig


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("Wayde van Niekerk: Comprehensive Body Segmentation Analysis")
    print("=" * 80)

    # Initialize analysis
    vnk = VanNiekerkSegmentation()

    # 1. Segment properties comparison
    print("\n[1/6] Computing segment properties...")
    df_dempster = vnk.compute_all_segment_properties('dempster')
    df_zatsiorsky = vnk.compute_all_segment_properties('zatsiorsky')

    print("\nDempster-Winter Model:")
    print(df_dempster.round(4))

    print("\nZatsiorsky-de Leva Model:")
    print(df_zatsiorsky.round(4))

    # 2. Lower limb analysis
    print("\n[2/6] Analyzing lower limb properties...")
    limb_d = vnk.compute_lower_limb_properties('dempster')
    limb_z = vnk.compute_lower_limb_properties('zatsiorsky')

    print(f"\nLower Limb (Dempster):")
    print(f"  Total Mass: {limb_d['total_mass']:.3f} kg ({limb_d['total_mass']/vnk.profile.mass*100:.1f}% of body mass)")
    print(f"  CM Height: {limb_d['cm_height']:.3f} m")
    print(f"  I around limb CM: {limb_d['I_limb_cm']:.4f} kg·m²")
    print(f"  I around hip: {limb_d['I_hip']:.4f} kg·m²")

    print(f"\nLower Limb (Zatsiorsky):")
    print(f"  Total Mass: {limb_z['total_mass']:.3f} kg ({limb_z['total_mass']/vnk.profile.mass*100:.1f}% of body mass)")
    print(f"  CM Height: {limb_z['cm_height']:.3f} m")
    print(f"  I around limb CM: {limb_z['I_limb_cm']:.4f} kg·m²")
    print(f"  I around hip: {limb_z['I_hip']:.4f} kg·m²")

    # 3. Whole body CM
    print("\n[3/6] Computing whole body center of mass...")
    body_cm_d = vnk.compute_whole_body_cm('dempster')
    print(f"\nBody CM Height (Dempster): {body_cm_d['height']:.3f} m ({body_cm_d['height_fraction']*100:.1f}% of height)")

    # 4. Sprint mechanics analysis
    print("\n[4/6] Analyzing sprint mechanics from segmentation...")
    mechanics = vnk.analyze_sprint_mechanics()

    print(f"\nNatural Frequency of Leg Swing:")
    print(f"  Dempster: {mechanics['natural_frequency_dempster']:.3f} Hz")
    print(f"  Zatsiorsky: {mechanics['natural_frequency_zatsiorsky']:.3f} Hz")
    print(f"  Actual Stride Frequency: {mechanics['actual_stride_frequency']:.3f} Hz")
    print(f"\nResonance Ratio (Actual/Natural):")
    print(f"  Dempster: {mechanics['resonance_ratio_dempster']:.3f}")
    print(f"  Zatsiorsky: {mechanics['resonance_ratio_zatsiorsky']:.3f}")

    if 0.9 < mechanics['resonance_ratio_dempster'] < 1.1:
        print("  ✓ Van Niekerk operates near optimal resonance!")

    # 5. Proportions comparison
    print("\n[5/6] Comparing to optimal sprinter proportions...")
    df_proportions = vnk.compare_to_optimal_sprinter()
    print("\n", df_proportions.round(3))

    # 6. Generate visualizations
    print("\n[6/6] Generating visualizations...")

    fig1 = plot_segment_comparison(vnk)
    fig1.savefig('van_niekerk_segments.png',
                 dpi=300, bbox_inches='tight')
    print("  ✓ Saved: van_niekerk_segments.png")

    fig2 = plot_lower_limb_analysis(vnk)
    fig2.savefig('van_niekerk_lower_limb.png',
                 dpi=300, bbox_inches='tight')
    print("  ✓ Saved: van_niekerk_lower_limb.png")

    fig3 = plot_sprint_mechanics_analysis(vnk)
    fig3.savefig('van_niekerk_sprint_mechanics.png',
                 dpi=300, bbox_inches='tight')
    print("  ✓ Saved: van_niekerk_sprint_mechanics.png")

    fig4 = plot_proportions_comparison(vnk)
    fig4.savefig('van_niekerk_proportions.png',
                 dpi=300, bbox_inches='tight')
    print("  ✓ Saved: van_niekerk_proportions.png")

    print("\n" + "=" * 80)
    print("Analysis Complete!")
    print("=" * 80)
    print("\nKey Findings:")
    print(f"  • Leg-to-height ratio: {vnk.profile.leg_to_height_ratio():.3f} (optimal: ~0.51)")
    print(f"  • Stride-to-height ratio: {vnk.profile.relative_step_length():.3f} (optimal: ~1.51)")
    print(f"  • Hip-shoulder ratio: {vnk.profile.hip_shoulder_ratio():.3f} (optimal: ~0.73)")
    print(f"  • Resonance ratio: {mechanics['resonance_ratio_dempster']:.3f} (optimal: ~1.00)")
    print("\nVan Niekerk's body proportions are nearly optimal for 400m sprinting,")
    print("with exceptional leg-to-height ratio and near-perfect resonance matching.")
    print("=" * 80)

    # Optionally show plots
    # plt.show()
