//! Data file parsers for various fitness tracking formats

pub mod fit;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Activity session data
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityData {
    /// Timestamps for each record
    pub timestamp: Vec<DateTime<Utc>>,

    /// Heart rate (bpm)
    pub heart_rate: Option<Vec<f64>>,

    /// Cadence (steps/min)
    pub cadence: Option<Vec<f64>>,

    /// Speed (m/s)
    pub speed: Option<Vec<f64>>,

    /// Altitude (m)
    pub altitude: Option<Vec<f64>>,

    /// Temperature (°C)
    pub temperature: Option<Vec<f64>>,

    /// Position latitude (degrees)
    pub position_lat: Option<Vec<f64>>,

    /// Position longitude (degrees)
    pub position_long: Option<Vec<f64>>,

    /// Vertical oscillation (cm)
    pub vertical_oscillation: Option<Vec<f64>>,

    /// Ground contact time (s)
    pub ground_contact_time: Option<Vec<f64>>,

    /// Stride length (m)
    pub stride_length: Option<Vec<f64>>,

    /// Power (watts)
    pub power: Option<Vec<f64>>,

    /// Session metadata
    pub metadata: HashMap<String, String>,
}

impl ActivityData {
    /// Create new empty activity data
    pub fn new() -> Self {
        Self {
            timestamp: Vec::new(),
            heart_rate: None,
            cadence: None,
            speed: None,
            altitude: None,
            temperature: None,
            position_lat: None,
            position_long: None,
            vertical_oscillation: None,
            ground_contact_time: None,
            stride_length: None,
            power: None,
            metadata: HashMap::new(),
        }
    }

    /// Get number of records
    pub fn len(&self) -> usize {
        self.timestamp.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.timestamp.is_empty()
    }

    /// Get duration in seconds
    pub fn duration_seconds(&self) -> f64 {
        if self.len() < 2 {
            return 0.0;
        }
        let duration = self.timestamp[self.len() - 1] - self.timestamp[0];
        duration.num_milliseconds() as f64 / 1000.0
    }

    /// Get sampling rate in Hz
    pub fn sampling_rate(&self) -> f64 {
        if self.len() < 2 {
            return 0.0;
        }
        let duration = self.duration_seconds();
        (self.len() - 1) as f64 / duration
    }
}

impl Default for ActivityData {
    fn default() -> Self {
        Self::new()
    }
}
