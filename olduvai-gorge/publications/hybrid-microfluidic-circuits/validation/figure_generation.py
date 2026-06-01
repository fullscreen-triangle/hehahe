"""
Publication Figure Generation - 4 Charts Per Row

Generates 6 publication-quality panels, each with 4 data-driven charts in a single row.
All charts are data-driven (no conceptual/text-based), with one 3D chart per panel.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path

from charge_dynamics import ClosedCircuit, create_circuit_config
from sensation_mechanics import SensationCategorizer, MultimodalSensation
from receptor_models import ReceptorComparison, ReceptorAdaptation
from temperature_effects import TemperatureModel, ThermalSensationAnalysis


class PublicationFigureGenerator:
    """Generate publication-quality 6-panel figures with 4 charts per row."""

    def __init__(self, output_dir='./figures'):
        """Initialize figure generator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        plt.rcParams.update({
            'figure.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.edgecolor': 'black',
            'axes.linewidth': 1.2,
            'font.size': 8,
            'font.family': 'sans-serif',
            'xtick.direction': 'out',
            'ytick.direction': 'out',
            'grid.alpha': 0.3,
            'grid.linestyle': '--'
        })

    def panel_1_charge_dynamics(self):
        """Panel 1: 4 charts in one row"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        # Chart 1: Exponential decay
        config = create_circuit_config(n_compartments=3)
        circuit = ClosedCircuit(config)
        Q0 = np.array([0.6, 0.3, 0.1])
        tau = 0.4
        result = circuit.simulate_perturbation(Q0, tau=tau, t_max=3.0, dt=0.01)

        axes[0].semilogy(result['time'], result['sensation_rate'], 'o-', color='#1f77b4',  markersize=3, linewidth=2)
        axes[0].semilogy(result['time'], result['sensation_rate_analytical'], '--', color='#d62728', linewidth=2.5)
        axes[0].set_xlabel('Time (s)', fontsize=9)
        axes[0].set_ylabel('Sensation Rate', fontsize=9)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Exponential Decay', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D Charge trajectory
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        t_subset = np.linspace(0, 2.0, 50)
        Q_subset = circuit.exponential_response(t_subset, Q0, tau)
        colors = cm.viridis(t_subset / np.max(t_subset))

        for i in range(len(t_subset)-1):
            ax.plot(Q_subset[0, i:i+2], Q_subset[1, i:i+2], Q_subset[2, i:i+2], color=colors[i], linewidth=2)

        ax.scatter(Q_subset[0, 0], Q_subset[1, 0], Q_subset[2, 0], c='green', s=80, marker='o', zorder=5)
        ax.scatter(Q_subset[0, -1], Q_subset[1, -1], Q_subset[2, -1], c='red', s=80, marker='s', zorder=5)
        ax.set_xlabel('q1', fontsize=8)
        ax.set_ylabel('q2', fontsize=8)
        ax.set_zlabel('q3', fontsize=8)
        ax.set_title('B. 3D Trajectory', fontsize=10, weight='bold')

        # Chart 3: Charge conservation
        Q_sum = np.sum(result['Q'], axis=0)
        deviation = np.abs(Q_sum - config.Q_total)
        axes[2].semilogy(result['time'], deviation + 1e-15, 'o-', color='#2ca02c', markersize=3, linewidth=2)
        axes[2].set_xlabel('Time (s)', fontsize=9)
        axes[2].set_ylabel('Charge Deviation', fontsize=9)
        axes[2].grid(True, alpha=0.3)
        axes[2].set_title('C. Conservation', fontsize=10, weight='bold', loc='left')

        # Chart 4: Sensation integral
        cumulative = np.cumsum(result['sensation_rate']) * 0.01
        axes[3].fill_between(result['time'], 0, cumulative, alpha=0.3, color='#ff7f0e')
        axes[3].plot(result['time'], cumulative, 'o-', color='#ff7f0e', markersize=3, linewidth=2)
        axes[3].axhline(result['Delta_Q'], color='red', linestyle='--', linewidth=2)
        axes[3].set_xlabel('Time (s)', fontsize=9)
        axes[3].set_ylabel('Cumulative', fontsize=9)
        axes[3].grid(True, alpha=0.3)
        axes[3].set_title('D. Integral', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_2_sensation_categorization(self):
        """Panel 2: Pain/pleasure categorization"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        categorizer = SensationCategorizer(tau_critical=0.05)

        # Chart 1: Temporal profiles
        taus = [0.02, 0.05, 0.15]
        colors = ['#d62728', '#ff7f0e', '#2ca02c']
        Delta_Q = 1.0
        t = np.linspace(0, 0.5, 200)

        for tau, color in zip(taus, colors):
            P = (Delta_Q / tau) * np.exp(-t / tau)
            axes[0].plot(t * 1000, P, linewidth=2.5, color=color)

        axes[0].set_xlabel('Time (ms)', fontsize=9)
        axes[0].set_ylabel('Sensation Rate', fontsize=9)
        axes[0].grid(True, alpha=0.3)
        axes[0].set_title('A. Temporal Profiles', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D surface
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        taus_range = np.logspace(-2.5, 0.5, 15)
        Delta_Q_range = np.linspace(0.5, 2.0, 12)
        taus_mesh, dQ_mesh = np.meshgrid(taus_range, Delta_Q_range)
        peak_sensation = dQ_mesh / taus_mesh

        ax.plot_surface(np.log10(taus_mesh), dQ_mesh, peak_sensation, cmap='viridis', alpha=0.8)
        ax.set_xlabel('log(tau)', fontsize=8)
        ax.set_ylabel('DeltaQ', fontsize=8)
        ax.set_zlabel('Peak', fontsize=8)
        ax.set_title('B. Response Surface', fontsize=10, weight='bold')

        # Chart 3: Category boundary
        taus_test = np.logspace(-2, 0.5, 100)
        for i, tau in enumerate(taus_test):
            cat = categorizer.categorize(tau)
            color = '#d62728' if cat.value == 'pain' else ('#2ca02c' if cat.value == 'pleasure' else '#ff7f0e')
            axes[2].scatter(tau * 1000, 1, c=color, s=40, zorder=2)

        axes[2].axvline(categorizer.tau_critical * 1000, color='red', linestyle='--', linewidth=2)
        axes[2].set_xscale('log')
        axes[2].set_xlabel('Time (ms)', fontsize=9)
        axes[2].set_ylim([0.5, 1.5])
        axes[2].set_yticks([])
        axes[2].grid(True, alpha=0.3, axis='x')
        axes[2].set_title('C. Category Boundary', fontsize=10, weight='bold', loc='left')

        # Chart 4: Cumulative
        t_long = np.linspace(0, 1.0, 300)
        for tau, color in zip(taus, colors):
            P = (Delta_Q / tau) * np.exp(-t_long / tau)
            cumsum = np.cumsum(P) * (t_long[1] - t_long[0])
            axes[3].plot(t_long * 1000, cumsum, linewidth=2.5, color=color)

        axes[3].set_xlabel('Time (ms)', fontsize=9)
        axes[3].set_ylabel('Cumulative', fontsize=9)
        axes[3].grid(True, alpha=0.3)
        axes[3].set_title('D. Cumulative', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_3_receptor_diversity(self):
        """Panel 3: Receptor diversity"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        tau_min, tau_max = 0.01, 1.0
        pop_diverse = ReceptorComparison.logarithmic_diverse_population(
            tau_min=tau_min, tau_max=tau_max, n_types=8,
            total_density=100.0, metabolic_cost=50.0
        )

        # Chart 1: Distribution
        taus_diverse = pop_diverse.tau_values()
        axes[0].bar(range(len(taus_diverse)), taus_diverse * 1000, color='#1f77b4', alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[0].set_xlabel('Receptor Type', fontsize=9)
        axes[0].set_ylabel('Time Constant (ms)', fontsize=9)
        axes[0].set_yscale('log')
        axes[0].grid(True, alpha=0.3, axis='y')
        axes[0].set_title('A. Distribution', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D Coverage
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        stimulus_taus = np.logspace(-2.2, 0.8, 30)
        receptor_taus = np.concatenate([taus_diverse, [np.sqrt(tau_min * tau_max)]])

        coverage_matrix = np.zeros((len(receptor_taus), len(stimulus_taus)))
        for i, r_tau in enumerate(receptor_taus):
            for j, s_tau in enumerate(stimulus_taus):
                freq_match = abs(r_tau - s_tau) / (r_tau + s_tau + 1e-10)
                coverage_matrix[i, j] = 1.0 if freq_match < 0.15 else 0.0

        stim_grid, rec_grid = np.meshgrid(np.log10(stimulus_taus), np.arange(len(receptor_taus)))
        ax.plot_surface(stim_grid, rec_grid, coverage_matrix, cmap='RdYlGn', alpha=0.8)
        ax.set_xlabel('log(tau)', fontsize=8)
        ax.set_ylabel('Receptor', fontsize=8)
        ax.set_zlabel('Detected', fontsize=8)
        ax.set_title('B. 3D Coverage', fontsize=10, weight='bold')

        # Chart 3: Coverage comparison
        stimulus_taus_test = np.logspace(-2.2, 0.8, 50)
        pop_mono = ReceptorComparison.monolithic_population(
            tau=np.sqrt(tau_min * tau_max), total_density=100.0, metabolic_cost=50.0
        )

        cov_mono = pop_mono.stimulus_coverage(stimulus_taus_test)
        cov_div = pop_diverse.stimulus_coverage(stimulus_taus_test)

        bars = axes[2].bar(['Monolithic', 'Diverse'], [cov_mono['coverage_fraction'], cov_div['coverage_fraction']],
                          color=['#d62728', '#2ca02c'], alpha=0.7, edgecolor='black', linewidth=1.2)
        axes[2].set_ylabel('Coverage', fontsize=9)
        axes[2].set_ylim([0, 1.0])
        axes[2].grid(True, alpha=0.3, axis='y')
        axes[2].set_title('C. Coverage', fontsize=10, weight='bold', loc='left')

        # Chart 4: Spacing
        spacing = pop_diverse.logarithmic_spacing_score()
        actual = np.array(spacing['actual_taus'])
        expected = np.array(spacing['expected_taus'])

        axes[3].loglog(expected * 1000, actual * 1000, 'o', color='#1f77b4', markersize=7, markeredgecolor='black', markeredgewidth=1.2)
        axes[3].loglog(expected * 1000, expected * 1000, '--', color='red', linewidth=2, alpha=0.7)
        axes[3].set_xlabel('Expected (ms)', fontsize=9)
        axes[3].set_ylabel('Actual (ms)', fontsize=9)
        axes[3].grid(True, alpha=0.3, which='both')
        axes[3].set_title('D. Spacing', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_4_temperature_effects(self):
        """Panel 4: Temperature"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        model = TemperatureModel(tau_ref=0.1, E_a=12000.0, T_ref=298.15)

        # Chart 1: Scaling
        temps_C = np.linspace(5, 45, 50)
        temps_K = temps_C + 273.15
        taus = np.array([model.timescale_at_temperature(T) for T in temps_K])

        axes[0].semilogy(temps_C, taus * 1000, 'o-', color='#d62728', markersize=4, linewidth=2.5)
        axes[0].set_xlabel('Temperature (C)', fontsize=9)
        axes[0].set_ylabel('Time Constant (ms)', fontsize=9)
        axes[0].grid(True, alpha=0.3, which='both')
        axes[0].set_title('A. Arrhenius Scaling', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D Surface
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        temps_grid = np.linspace(5, 45, 20)
        dq_grid = np.linspace(0.5, 2.0, 15)
        temps_K_grid = temps_grid + 273.15
        temps_mesh, dq_mesh = np.meshgrid(temps_grid, dq_grid)
        sensation_mesh = np.zeros_like(temps_mesh)

        for i in range(len(dq_grid)):
            for j in range(len(temps_grid)):
                tau = model.timescale_at_temperature(temps_K_grid[j])
                sensation_mesh[i, j] = dq_mesh[i, j] / tau * 1000

        ax.plot_surface(temps_mesh, dq_mesh, sensation_mesh, cmap='plasma', alpha=0.8)
        ax.set_xlabel('Temp (C)', fontsize=8)
        ax.set_ylabel('DeltaQ', fontsize=8)
        ax.set_zlabel('Peak Rate', fontsize=8)
        ax.set_title('B. 3D Thermal Surface', fontsize=10, weight='bold')

        # Chart 3: Q10
        temp_pairs = [(10, 20), (15, 25), (20, 30), (25, 35), (30, 40)]
        q10_vals = []
        temp_ctrs = []

        for t_low, t_high in temp_pairs:
            tau_low = model.timescale_at_temperature(t_low + 273.15)
            tau_high = model.timescale_at_temperature(t_high + 273.15)
            q10_vals.append(tau_high / tau_low)
            temp_ctrs.append((t_low + t_high) / 2)

        axes[2].plot(temp_ctrs, q10_vals, 'o-', color='#1f77b4', markersize=7, linewidth=2.5, markeredgecolor='black', markeredgewidth=1.2)
        axes[2].set_xlabel('Temperature (C)', fontsize=9)
        axes[2].set_ylabel('Q10', fontsize=9)
        axes[2].grid(True, alpha=0.3)
        axes[2].set_title('C. Q10 Coefficient', fontsize=10, weight='bold', loc='left')

        # Chart 4: Warm/Cold dominance
        analyzer = ThermalSensationAnalysis()
        warm_cold = analyzer.warm_cold_sensation_crossover()
        temps_display = np.array(warm_cold['temperatures_C'])
        dominance = np.array(warm_cold['dominance_index'])

        colors_temp = np.where(dominance > 0, '#d62728', '#2ca02c')
        axes[3].scatter(temps_display, dominance, c=colors_temp, s=60, edgecolor='black', linewidth=1.2, zorder=3)
        axes[3].axhline(0, color='black', linewidth=1.5)
        axes[3].axvline(warm_cold['crossover_temperature_C'], color='blue', linestyle='--', linewidth=2)
        axes[3].set_xlabel('Temperature (C)', fontsize=9)
        axes[3].set_ylabel('Dominance Index', fontsize=9)
        axes[3].set_ylim([-1.1, 1.1])
        axes[3].grid(True, alpha=0.3)
        axes[3].set_title('D. Warm/Cold', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_5_multimodal_coupling(self):
        """Panel 5: Multi-circuit frequency matching"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        integrator = MultimodalSensation(freq_match_threshold=0.1)
        modality_taus = np.array([0.02, 0.05, 0.1, 0.5])
        modality_names = ['Pain', 'Pressure', 'Temp', 'Pleasure']

        # Chart 1: Matching matrix
        matching_matrix = np.zeros((len(modality_taus), len(modality_taus)))
        for i in range(len(modality_taus)):
            for j in range(len(modality_taus)):
                matching_matrix[i, j] = integrator.frequency_matching_score(
                    modality_taus[i], modality_taus[j]
                )

        im = axes[0].imshow(matching_matrix, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=1)
        axes[0].set_xticks(range(len(modality_names)))
        axes[0].set_yticks(range(len(modality_names)))
        axes[0].set_xticklabels(modality_names, fontsize=8)
        axes[0].set_yticklabels(modality_names, fontsize=8)
        axes[0].set_title('A. Matching Matrix', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D Coupling landscape
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        tau1_range = np.logspace(-2, 0, 12)
        tau2_range = np.logspace(-2, 0, 12)
        t1_mesh, t2_mesh = np.meshgrid(tau1_range, tau2_range)
        coupling = np.zeros_like(t1_mesh)

        for i in range(len(tau1_range)):
            for j in range(len(tau2_range)):
                coupling[j, i] = 1.0 if integrator.is_frequency_matched(t1_mesh[j, i], t2_mesh[j, i]) else 0.0

        ax.plot_surface(np.log10(t1_mesh), np.log10(t2_mesh), coupling, cmap='coolwarm', alpha=0.8)
        ax.set_xlabel('log(tau1)', fontsize=8)
        ax.set_ylabel('log(tau2)', fontsize=8)
        ax.set_zlabel('Couples', fontsize=8)
        ax.set_title('B. 3D Landscape', fontsize=10, weight='bold')

        # Chart 3: Integration profile
        t_couple = np.linspace(0, 0.5, 200)
        tau_fast = 0.02
        tau_slow = 0.025
        P1 = (1.0 / tau_fast) * np.exp(-t_couple / tau_fast)
        P2 = (1.0 / tau_slow) * np.exp(-t_couple / tau_slow)
        P_int = np.abs(P1 + P2) / 2

        axes[2].fill_between(t_couple * 1000, 0, P1, alpha=0.2, color='#d62728')
        axes[2].fill_between(t_couple * 1000, 0, P2, alpha=0.2, color='#2ca02c')
        axes[2].plot(t_couple * 1000, P_int, linewidth=2.5, color='#1f77b4')
        axes[2].set_xlabel('Time (ms)', fontsize=9)
        axes[2].set_ylabel('Sensation Rate', fontsize=9)
        axes[2].set_xlim([0, 100])
        axes[2].grid(True, alpha=0.3)
        axes[2].set_title('C. Matched Integration', fontsize=10, weight='bold', loc='left')

        # Chart 4: Multi-modal temporal
        mods = [
            {'name': 'Pain', 'tau': 0.02, 'color': '#d62728'},
            {'name': 'Pressure', 'tau': 0.05, 'color': '#ff7f0e'},
            {'name': 'Temp', 'tau': 0.1, 'color': '#2ca02c'},
            {'name': 'Pleasure', 'tau': 0.3, 'color': '#1f77b4'}
        ]

        t_overlap = np.linspace(0, 0.4, 200)
        for mod in mods:
            P = (1.0 / mod['tau']) * np.exp(-t_overlap / mod['tau'])
            axes[3].plot(t_overlap * 1000, P, linewidth=2.5, label=mod['name'], color=mod['color'])

        axes[3].set_xlabel('Time (ms)', fontsize=9)
        axes[3].set_ylabel('Sensation Rate', fontsize=9)
        axes[3].grid(True, alpha=0.3)
        axes[3].legend(fontsize=7, loc='upper right')
        axes[3].set_title('D. Multi-Modal Overlap', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def panel_6_adaptation_learning(self):
        """Panel 6: Receptor adaptation"""
        fig, axes = plt.subplots(1, 4, figsize=(22, 4.5))
        fig.patch.set_facecolor('white')

        pop_initial = ReceptorComparison.logarithmic_diverse_population(
            tau_min=0.01, tau_max=1.0, n_types=6,
            total_density=100.0, metabolic_cost=50.0
        )

        adapter = ReceptorAdaptation(pop_initial)
        stimulus_taus = np.logspace(-2, 0, 100)
        stimulus_weights = np.exp(-((np.log10(stimulus_taus) - (-0.5))**2) / 0.1)
        stimulus_weights /= np.sum(stimulus_weights)

        adaptation_history = adapter.multiple_adaptation_steps(
            stimulus_taus, stimulus_weights, n_steps=6
        )

        # Chart 1: Evolution
        steps = list(range(len(adaptation_history) + 1))
        initial_taus = pop_initial.tau_values() * 1000

        for i, tau_initial in enumerate(initial_taus):
            taus_over_time = [tau_initial]
            for hist in adaptation_history:
                new_tau = hist['new_tau'] * 1000 if 'new_tau' in hist else tau_initial
                taus_over_time.append(new_tau)
            axes[0].plot(steps[:len(taus_over_time)], taus_over_time, 'o-', markersize=5, linewidth=2, alpha=0.7)

        axes[0].set_xlabel('Adaptation Step', fontsize=9)
        axes[0].set_ylabel('Time Constant (ms)', fontsize=9)
        axes[0].set_yscale('log')
        axes[0].grid(True, alpha=0.3, which='both')
        axes[0].set_title('A. Evolution', fontsize=10, weight='bold', loc='left')

        # Chart 2: 3D Adaptation landscape
        ax = fig.add_axes([0.27, 0.15, 0.18, 0.8], projection='3d')
        steps_3d = np.arange(len(adaptation_history) + 1)
        stimulus_sample = np.logspace(-2, 0, 15)
        final_taus = adapter.current_population.tau_values()

        X = np.linspace(0, len(steps_3d)-1, 15)
        Y = np.log10(stimulus_sample)
        X, Y = np.meshgrid(X, Y)
        Z = np.zeros_like(X)

        for i, s_tau in enumerate(stimulus_sample):
            for j in range(len(X[0, :])):
                closest = min(final_taus, key=lambda t: abs(np.log10(t) - np.log10(s_tau)))
                Z[i, j] = -abs(np.log10(closest) - np.log10(s_tau))

        ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.8)
        ax.set_xlabel('Step', fontsize=8)
        ax.set_ylabel('log(tau)', fontsize=8)
        ax.set_zlabel('Match', fontsize=8)
        ax.set_title('B. 3D Landscape', fontsize=10, weight='bold')

        # Chart 3: Distribution
        axes[2].fill_between(np.log10(stimulus_taus), 0, stimulus_weights, alpha=0.3, color='#1f77b4')
        axes[2].plot(np.log10(stimulus_taus), stimulus_weights, linewidth=2.5, color='#1f77b4')

        final_receptor_taus = adapter.current_population.tau_values()
        for tau in final_receptor_taus:
            axes[2].axvline(np.log10(tau), color='red', linestyle='--', linewidth=1.5, alpha=0.6)

        axes[2].set_xlabel('log(Time Constant)', fontsize=9)
        axes[2].set_ylabel('Probability', fontsize=9)
        axes[2].grid(True, alpha=0.3)
        axes[2].set_title('C. Distribution', fontsize=10, weight='bold', loc='left')

        # Chart 4: Spacing quality
        spacing_initial = pop_initial.logarithmic_spacing_score()
        log_errors = [spacing_initial['mean_log_error']]

        for hist in adaptation_history:
            if 'population_spacing' in hist:
                log_errors.append(hist['population_spacing']['mean_log_error'])

        axes[3].plot(steps[:len(log_errors)], log_errors, 'o-', color='#2ca02c', markersize=7, linewidth=2.5, markeredgecolor='black', markeredgewidth=1.2)
        axes[3].axhline(0.1, color='gray', linestyle='--', linewidth=1.5)
        axes[3].set_xlabel('Adaptation Step', fontsize=9)
        axes[3].set_ylabel('Log Error', fontsize=9)
        axes[3].grid(True, alpha=0.3)
        axes[3].set_title('D. Spacing Quality', fontsize=10, weight='bold', loc='left')

        plt.tight_layout()
        return fig

    def generate_all_panels(self):
        """Generate all 6 panels."""
        panels = [
            (self.panel_1_charge_dynamics, 'Panel_1_Charge_Dynamics'),
            (self.panel_2_sensation_categorization, 'Panel_2_Sensation_Categorization'),
            (self.panel_3_receptor_diversity, 'Panel_3_Receptor_Diversity'),
            (self.panel_4_temperature_effects, 'Panel_4_Temperature_Effects'),
            (self.panel_5_multimodal_coupling, 'Panel_5_Multimodal_Coupling'),
            (self.panel_6_adaptation_learning, 'Panel_6_Adaptation_Learning')
        ]

        results = {}
        for panel_func, panel_name in panels:
            print(f"Generating {panel_name}...")
            fig = panel_func()

            filepath_pdf = self.output_dir / f'{panel_name}.pdf'
            fig.savefig(filepath_pdf, dpi=300, bbox_inches='tight', facecolor='white')

            filepath_png = self.output_dir / f'{panel_name}.png'
            fig.savefig(filepath_png, dpi=300, bbox_inches='tight', facecolor='white')

            plt.close(fig)

            results[panel_name] = {
                'pdf': str(filepath_pdf),
                'png': str(filepath_png)
            }

        return results


def main():
    """Main execution."""
    print("\nGenerating publication figures...")
    generator = PublicationFigureGenerator(output_dir='./publication_figures')
    results = generator.generate_all_panels()

    print("\nGenerated files:")
    for panel_name, files in results.items():
        print(f"  {panel_name}: {len(files)} formats")

    return results


if __name__ == '__main__':
    main()
