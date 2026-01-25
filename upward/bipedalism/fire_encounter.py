"""
FIRE ENCOUNTER INEVITABILITY SIMULATION

Validates: Fire encounters were statistically inevitable
           for hominids in C4 grassland environments

Based on: Sachikonye (2025) - Origins of Bipedalism
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import poisson
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

class FireEncounterModel:
    """
    Model fire encounter probability for hominid groups
    during C4 grassland expansion (8-3 Mya)
    """

    def __init__(self):
        # Parameters from paper
        self.lightning_strike_freq = 0.025  # strikes/km²/day (conservative)
        self.territory_area = 10  # km²
        self.dry_season_duration = 150  # days
        self.c4_coverage = 0.7  # 70% C4 grass coverage
        self.ignition_probability = 0.7  # probability strike causes fire

        # Parameter ranges for sensitivity analysis
        self.lambda_range = np.linspace(0.020, 0.035, 50)  # strike frequency
        self.area_range = np.linspace(5, 20, 50)  # territory size
        self.c4_range = np.linspace(0.4, 0.9, 50)  # C4 coverage
        self.time_range = np.linspace(-8, -3, 50)  # Mya (8-3 million years ago)

    def calculate_fire_probability(self, lambda_val, area, duration,
                                   c4_coverage, ignition_prob):
        """
        Calculate probability of fire encounter

        P(F) = 1 - exp(-λATϕψ)

        Parameters:
        -----------
        lambda_val : float
            Lightning strike frequency (strikes/km²/day)
        area : float
            Territory area (km²)
        duration : float
            Dry season duration (days)
        c4_coverage : float
            C4 grass coverage fraction (0-1)
        ignition_prob : float
            Probability strike causes fire (0-1)
        """
        exponent = lambda_val * area * duration * c4_coverage * ignition_prob
        prob = 1.0 - np.exp(-exponent)
        return prob

    def calculate_expected_fires(self, lambda_val, area, duration,
                                c4_coverage, ignition_prob):
        """
        Calculate expected number of fire encounters
        """
        return lambda_val * area * duration * c4_coverage * ignition_prob

    def baseline_probability(self):
        """
        Calculate baseline probability from paper
        """
        prob = self.calculate_fire_probability(
            self.lightning_strike_freq,
            self.territory_area,
            self.dry_season_duration,
            self.c4_coverage,
            self.ignition_probability
        )

        expected = self.calculate_expected_fires(
            self.lightning_strike_freq,
            self.territory_area,
            self.dry_season_duration,
            self.c4_coverage,
            self.ignition_probability
        )

        return prob, expected

    def sensitivity_analysis_2d(self):
        """
        2D sensitivity analysis: Territory size vs. C4 coverage
        """
        prob_grid = np.zeros((len(self.area_range), len(self.c4_range)))

        for i, area in enumerate(self.area_range):
            for j, c4 in enumerate(self.c4_range):
                prob_grid[i, j] = self.calculate_fire_probability(
                    self.lightning_strike_freq,
                    area,
                    self.dry_season_duration,
                    c4,
                    self.ignition_probability
                )

        return prob_grid

    def temporal_evolution(self):
        """
        Model C4 expansion over time (8-3 Mya)
        """
        # C4 coverage increased from ~20% to ~70% over this period
        c4_coverage_over_time = 0.2 + (0.7 - 0.2) * (
            (self.time_range + 8) / 5  # Normalize to 0-1 over 5 Myr
        )

        probabilities = []
        expected_fires = []

        for c4 in c4_coverage_over_time:
            prob = self.calculate_fire_probability(
                self.lightning_strike_freq,
                self.territory_area,
                self.dry_season_duration,
                c4,
                self.ignition_probability
            )
            exp_fires = self.calculate_expected_fires(
                self.lightning_strike_freq,
                self.territory_area,
                self.dry_season_duration,
                c4,
                self.ignition_probability
            )
            probabilities.append(prob)
            expected_fires.append(exp_fires)

        return c4_coverage_over_time, probabilities, expected_fires

    def spatial_variation(self, n_territories=1000):
        """
        Simulate spatial variation across multiple territories
        """
        # Random variation in parameters
        lambda_vals = np.random.normal(0.025, 0.005, n_territories)
        lambda_vals = np.clip(lambda_vals, 0.015, 0.040)

        areas = np.random.normal(10, 3, n_territories)
        areas = np.clip(areas, 5, 20)

        c4_vals = np.random.beta(7, 3, n_territories)  # Skewed toward high C4

        probabilities = []
        expected_fires = []

        for lam, area, c4 in zip(lambda_vals, areas, c4_vals):
            prob = self.calculate_fire_probability(
                lam, area, self.dry_season_duration,
                c4, self.ignition_probability
            )
            exp = self.calculate_expected_fires(
                lam, area, self.dry_season_duration,
                c4, self.ignition_probability
            )
            probabilities.append(prob)
            expected_fires.append(exp)

        return np.array(probabilities), np.array(expected_fires)

    def plot_comprehensive_analysis(self, save_path='fire_encounter_analysis.pdf'):
        """
        Create comprehensive figure with all analyses
        """
        fig = plt.figure(figsize=(16, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Panel A: Baseline calculation
        ax1 = fig.add_subplot(gs[0, 0])
        prob, expected = self.baseline_probability()

        ax1.text(0.5, 0.7, f'Baseline Parameters:',
                ha='center', fontsize=12, fontweight='bold',
                transform=ax1.transAxes)
        ax1.text(0.5, 0.55, f'Territory: {self.territory_area} km²',
                ha='center', fontsize=10, transform=ax1.transAxes)
        ax1.text(0.5, 0.45, f'C4 Coverage: {self.c4_coverage*100:.0f}%',
                ha='center', fontsize=10, transform=ax1.transAxes)
        ax1.text(0.5, 0.35, f'Dry Season: {self.dry_season_duration} days',
                ha='center', fontsize=10, transform=ax1.transAxes)

        ax1.text(0.5, 0.15, f'P(Fire) = {prob:.4f}',
                ha='center', fontsize=14, fontweight='bold',
                transform=ax1.transAxes, color='red')
        ax1.text(0.5, 0.05, f'Expected fires/season: {expected:.1f}',
                ha='center', fontsize=11, transform=ax1.transAxes)

        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
        ax1.axis('off')
        ax1.set_title('A. Baseline Fire Encounter', fontsize=13,
                     fontweight='bold', loc='left', pad=10)

        # Panel B: 2D Sensitivity (Territory vs C4)
        ax2 = fig.add_subplot(gs[0, 1:])
        prob_grid = self.sensitivity_analysis_2d()

        im = ax2.contourf(self.c4_range * 100, self.area_range, prob_grid,
                         levels=20, cmap='YlOrRd')
        contours = ax2.contour(self.c4_range * 100, self.area_range, prob_grid,
                              levels=[0.5, 0.9, 0.99, 0.999],
                              colors='black', linewidths=1.5)
        ax2.clabel(contours, inline=True, fontsize=9, fmt='%.3f')

        # Mark baseline point
        ax2.plot(self.c4_coverage * 100, self.territory_area,
                'w*', markersize=20, markeredgecolor='black',
                markeredgewidth=2, label='Baseline')

        ax2.set_xlabel('C4 Grass Coverage (%)', fontsize=11)
        ax2.set_ylabel('Territory Area (km²)', fontsize=11)
        ax2.set_title('B. Sensitivity Analysis: Fire Encounter Probability',
                     fontsize=13, fontweight='bold', loc='left', pad=10)
        ax2.legend(fontsize=10)

        cbar = plt.colorbar(im, ax=ax2)
        cbar.set_label('P(Fire Encounter)', fontsize=10)

        # Panel C: Temporal Evolution
        ax3 = fig.add_subplot(gs[1, :])
        c4_time, prob_time, exp_time = self.temporal_evolution()

        ax3_twin = ax3.twinx()

        line1 = ax3.plot(self.time_range, np.array(prob_time) * 100,
                        'b-', linewidth=3, label='Fire Probability')
        line2 = ax3_twin.plot(self.time_range, c4_time * 100,
                             'g--', linewidth=2, label='C4 Coverage')

        # Shade "inevitable fire" region
        ax3.axhspan(99, 100, alpha=0.2, color='red',
                   label='Inevitable Fire Zone')

        ax3.set_xlabel('Time (Million Years Ago)', fontsize=12)
        ax3.set_ylabel('Fire Encounter Probability (%)', fontsize=12, color='b')
        ax3_twin.set_ylabel('C4 Grass Coverage (%)', fontsize=12, color='g')

        ax3.tick_params(axis='y', labelcolor='b')
        ax3_twin.tick_params(axis='y', labelcolor='g')

        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax3.legend(lines, labels, fontsize=10, loc='upper left')

        ax3.set_title('C. Temporal Evolution: C4 Expansion & Fire Probability (8-3 Mya)',
                     fontsize=13, fontweight='bold', loc='left', pad=10)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-8, -3)

        # Panel D: Spatial Variation
        ax4 = fig.add_subplot(gs[2, 0])
        probs_spatial, fires_spatial = self.spatial_variation(n_territories=1000)

        ax4.hist(probs_spatial, bins=50, color='orange', alpha=0.7,
                edgecolor='black')
        ax4.axvline(probs_spatial.mean(), color='red', linestyle='--',
                   linewidth=2, label=f'Mean: {probs_spatial.mean():.3f}')
        ax4.axvline(0.99, color='blue', linestyle='--',
                   linewidth=2, label='99% threshold')

        ax4.set_xlabel('Fire Encounter Probability', fontsize=11)
        ax4.set_ylabel('Number of Territories', fontsize=11)
        ax4.set_title('D. Spatial Variation (n=1000 territories)',
                     fontsize=13, fontweight='bold', loc='left', pad=10)
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3, axis='y')

        # Panel E: Expected Fires Distribution
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.hist(fires_spatial, bins=50, color='red', alpha=0.7,
                edgecolor='black')
        ax5.axvline(fires_spatial.mean(), color='darkred', linestyle='--',
                   linewidth=2, label=f'Mean: {fires_spatial.mean():.1f}')

        ax5.set_xlabel('Expected Fires per Season', fontsize=11)
        ax5.set_ylabel('Number of Territories', fontsize=11)
        ax5.set_title('E. Expected Fire Encounters',
                     fontsize=13, fontweight='bold', loc='left', pad=10)
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3, axis='y')

        # Panel F: Poisson Distribution
        ax6 = fig.add_subplot(gs[2, 2])

        # Calculate Poisson distribution for expected fires
        lambda_poisson = fires_spatial.mean()
        x_poisson = np.arange(0, 30)
        y_poisson = poisson.pmf(x_poisson, lambda_poisson)

        ax6.bar(x_poisson, y_poisson, color='purple', alpha=0.7,
               edgecolor='black')
        ax6.axvline(lambda_poisson, color='red', linestyle='--',
                   linewidth=2, label=f'λ = {lambda_poisson:.1f}')

        # Probability of zero fires
        p_zero = poisson.pmf(0, lambda_poisson)
        ax6.text(0.95, 0.95, f'P(0 fires) = {p_zero:.6f}',
                transform=ax6.transAxes, ha='right', va='top',
                fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat'))

        ax6.set_xlabel('Number of Fires', fontsize=11)
        ax6.set_ylabel('Probability', fontsize=11)
        ax6.set_title('F. Poisson Distribution',
                     fontsize=13, fontweight='bold', loc='left', pad=10)
        ax6.legend(fontsize=9)
        ax6.grid(True, alpha=0.3, axis='y')
        ax6.set_xlim(-0.5, 25)

        # Overall title
        fig.suptitle('Fire Encounter Inevitability in C4 Grassland Environments\n' +
                    'Validation of Sachikonye (2025) Fire Circle Hypothesis',
                    fontsize=15, fontweight='bold', y=0.995)

        # Save
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.savefig(save_path.replace('.pdf', '.png'), dpi=300,
                   bbox_inches='tight')

        print(f"\nFigure saved: {save_path}")

        return fig

    def print_results(self):
        """
        Print comprehensive results
        """
        print("="*70)
        print("FIRE ENCOUNTER PROBABILITY ANALYSIS")
        print("Validation of Fire Circle Hypothesis")
        print("="*70)

        prob, expected = self.baseline_probability()

        print("\nBASELINE PARAMETERS:")
        print(f"  Lightning frequency: {self.lightning_strike_freq} strikes/km²/day")
        print(f"  Territory area: {self.territory_area} km²")
        print(f"  Dry season: {self.dry_season_duration} days")
        print(f"  C4 coverage: {self.c4_coverage*100:.0f}%")
        print(f"  Ignition probability: {self.ignition_probability*100:.0f}%")

        print("\nRESULTS:")
        print(f"  Fire encounter probability: {prob:.6f} ({prob*100:.4f}%)")
        print(f"  Expected fires per season: {expected:.2f}")
        print(f"  Probability of ZERO fires: {(1-prob):.10f}")

        print("\nINTERPRETATION:")
        if prob > 0.999:
            print("  ✓ Fire encounters were STATISTICALLY INEVITABLE")
            print("  ✓ Hominids encountered fire every single season")
            print("  ✓ Fire exposure was unavoidable environmental pressure")

        # Spatial analysis
        probs_spatial, fires_spatial = self.spatial_variation(1000)
        print(f"\nSPATIAL VARIATION (1000 territories):")
        print(f"  Mean probability: {probs_spatial.mean():.4f}")
        print(f"  Territories with P > 0.99: {(probs_spatial > 0.99).sum()}/1000")
        print(f"  Territories with P > 0.999: {(probs_spatial > 0.999).sum()}/1000")
        print(f"  Mean expected fires: {fires_spatial.mean():.2f}")

        # Temporal
        c4_time, prob_time, exp_time = self.temporal_evolution()
        print(f"\nTEMPORAL EVOLUTION:")
        print(f"  At 8 Mya (20% C4): P = {prob_time[0]:.4f}")
        print(f"  At 5 Mya (50% C4): P = {prob_time[len(prob_time)//2]:.4f}")
        print(f"  At 3 Mya (70% C4): P = {prob_time[-1]:.4f}")

        print("\n" + "="*70)
        print("CONCLUSION:")
        print("Fire encounters were inevitable for hominids in C4 grasslands.")
        print("This validates the Fire Circle Hypothesis foundation.")
        print("="*70)

# Run the analysis
if __name__ == '__main__':
    model = FireEncounterModel()
    model.print_results()
    model.plot_comprehensive_analysis()
