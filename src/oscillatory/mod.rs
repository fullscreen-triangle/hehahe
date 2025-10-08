//! Multi-scale oscillatory analysis modules

pub mod hierarchy;
pub mod coupling;
pub mod frequency;
pub mod gear_ratio;

/// Hierarchical scale definitions
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Scale {
    /// Quantum membrane dynamics (10^12 - 10^15 Hz)
    QuantumMembrane = 0,

    /// Intracellular circuits (10^3 - 10^6 Hz)
    Intracellular = 1,

    /// Cellular information (0.1 - 100 Hz)
    Cellular = 2,

    /// Tissue integration (0.01 - 10 Hz)
    Tissue = 3,

    /// Neural processing (1 - 100 Hz)
    Neural = 4,

    /// Neuromuscular control (0.01 - 20 Hz)
    Neuromuscular = 5,

    /// Cardiovascular oscillations (0.01 - 5 Hz)
    Cardiovascular = 6,

    /// Locomotor patterns (0.5 - 3 Hz)
    Locomotor = 7,

    /// Circadian rhythms (10^-5 Hz)
    Circadian = 8,

    /// Allometric scaling (10^-8 - 10^-5 Hz)
    Allometric = 9,
}

impl Scale {
    /// Get frequency band for this scale (min, max) in Hz
    pub fn frequency_band(&self) -> (f64, f64) {
        match self {
            Scale::QuantumMembrane => (1e12, 1e15),
            Scale::Intracellular => (1e3, 1e6),
            Scale::Cellular => (0.1, 100.0),
            Scale::Tissue => (0.01, 10.0),
            Scale::Neural => (1.0, 100.0),
            Scale::Neuromuscular => (0.01, 20.0),
            Scale::Cardiovascular => (0.01, 5.0),
            Scale::Locomotor => (0.5, 3.0),
            Scale::Circadian => (1e-5, 1e-4),
            Scale::Allometric => (1e-8, 1e-5),
        }
    }

    /// Check if this scale is measurable by consumer sensors
    pub fn is_measurable(&self) -> bool {
        matches!(
            self,
            Scale::Neural
                | Scale::Neuromuscular
                | Scale::Cardiovascular
                | Scale::Locomotor
                | Scale::Circadian
        )
    }

    /// Get all scales in hierarchical order
    pub fn all() -> Vec<Scale> {
        vec![
            Scale::QuantumMembrane,
            Scale::Intracellular,
            Scale::Cellular,
            Scale::Tissue,
            Scale::Neural,
            Scale::Neuromuscular,
            Scale::Cardiovascular,
            Scale::Locomotor,
            Scale::Circadian,
            Scale::Allometric,
        ]
    }

    /// Get measurable scales only
    pub fn measurable() -> Vec<Scale> {
        vec![
            Scale::Neural,
            Scale::Neuromuscular,
            Scale::Cardiovascular,
            Scale::Locomotor,
            Scale::Circadian,
        ]
    }
}
