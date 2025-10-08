//! Multi-Scale Oscillatory Coupling Framework for Biomechanics
//!
//! This library implements the mathematical framework for analyzing human biomechanics
//! through multi-scale oscillatory coupling principles using consumer-grade wearable
//! sensor data.
//!
//! # Architecture
//!
//! The framework consists of several key modules:
//!
//! - `parsers`: Data file parsers for FIT, GPX, TCX, and KML formats
//! - `oscillatory`: Multi-scale oscillatory analysis and coupling computation
//! - `state_space`: Tri-dimensional state coordinate calculation
//! - `models`: Predictive models for performance, sleep quality, and injury risk
//! - `utils`: Signal processing and mathematical utilities
//!
//! # Example
//!
//! ```rust,no_run
//! use hehahe::parsers::fit::parse_fit_file;
//! use hehahe::oscillatory::coupling::compute_coupling_strength;
//!
//! // Load FIT file
//! let activity = parse_fit_file("activity.fit")?;
//!
//! // Compute multi-scale coupling
//! let coupling = compute_coupling_strength(&activity)?;
//!
//! println!("Coupling strength: {:.3}", coupling);
//! # Ok::<(), Box<dyn std::error::Error>>(())
//! ```

#![warn(missing_docs)]
#![warn(rustdoc::missing_crate_level_docs)]

pub mod oscillatory;
pub mod parsers;
pub mod models;
pub mod state_space;
pub mod utils;

/// Result type alias for the library
pub type Result<T> = std::result::Result<T, Error>;

/// Error types for the library
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// File I/O error
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// FIT file parsing error
    #[error("FIT parsing error: {0}")]
    FitParsing(String),

    /// Data validation error
    #[error("Data validation error: {0}")]
    Validation(String),

    /// Computation error
    #[error("Computation error: {0}")]
    Computation(String),

    /// Missing required data
    #[error("Missing required data: {0}")]
    MissingData(String),
}
