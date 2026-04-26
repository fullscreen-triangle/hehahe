/**
 * Body region catalogue — maps every SVG path id in HumanBody.jsx to
 * (a) a human-readable name, (b) the framework compartment that excites it,
 * (c) a one-line physiological note, and (d) an optional GLB submodel
 * that gives the detailed "look inside" view.
 *
 * Compartments match the charge calculator:
 *   motor       → cyan glow         (arms/legs/shoulders/hands/feet)
 *   thought     → violet glow       (head / brain)
 *   perception  → amber glow        (eyes / ears / sensory viscera)
 *   baseline    → soft white        (trunk housekeeping)
 *   cardiac     → red pulse         (heart)
 *   respiratory → teal              (lungs, trachea)
 *   visceral    → warm grey         (digestive)
 */

export const COMPARTMENT = {
  motor:       { colour: "#58E6D9", label: "Motor"       },
  thought:     { colour: "#B63E96", label: "Thought"     },
  perception:  { colour: "#F0A830", label: "Perception"  },
  baseline:    { colour: "#cfcfe2", label: "Baseline"    },
  cardiac:     { colour: "#E6395A", label: "Cardiac"     },
  respiratory: { colour: "#4FD1C5", label: "Respiratory" },
  visceral:    { colour: "#C7A972", label: "Visceral"    },
};

// Every path id defined in HumanBody.jsx. `surface` = modela.png view,
// `internal` = modelb.png view.
export const REGIONS = {
  // Surface (external) regions
  ana1:  { name: "head",          side: "surface", compartment: "thought",    info: "Whole-head partition. Aggregate cortical capacitance C_brain ≈ 1 mF.", glb: "bust.glb" },
  ana2:  { name: "right eye",     side: "surface", compartment: "perception", info: "Visual input channel. External perception bandwidth.", glb: null },
  ana3:  { name: "left eye",      side: "surface", compartment: "perception", info: "Visual input channel.", glb: null },
  ana4:  { name: "right ear",     side: "surface", compartment: "perception", info: "Auditory + vestibular input. Closes postural reflex loop.", glb: null },
  ana5:  { name: "left ear",      side: "surface", compartment: "perception", info: "Auditory + vestibular input.", glb: null },
  ana6:  { name: "nose",          side: "surface", compartment: "perception", info: "Olfactory + respiratory input.", glb: null },
  ana7:  { name: "mouth",         side: "surface", compartment: "perception", info: "Proprioceptive + gustatory input.", glb: null },
  ana8:  { name: "neck",          side: "surface", compartment: "baseline",   info: "Cervical spine, vagal trunk. Carries the autonomic return path.", glb: null },
  ana9:  { name: "chest",         side: "surface", compartment: "baseline",   info: "Ribcage and pectoral surface. Respiratory cage.", glb: "thorax_and_abdomen_a_few_important_muscles.glb" },
  ana10: { name: "abdomen",       side: "surface", compartment: "visceral",   info: "Abdominal wall. Digestive and autonomic traffic.", glb: "thorax_and_abdomen_a_few_important_muscles.glb" },
  ana11: { name: "pelvis",        side: "surface", compartment: "baseline",   info: "Pelvic girdle — anchor of the motor circuit's lower half.", glb: null },
  ana12: { name: "pubis",         side: "surface", compartment: "baseline",   info: "Pubic region.", glb: null },
  ana13: { name: "right shoulder",side: "surface", compartment: "motor",      info: "Glenohumeral joint. Entry point of upper-limb motor charge.", glb: "upper-body-explosion.glb" },
  ana14: { name: "left shoulder", side: "surface", compartment: "motor",      info: "Glenohumeral joint.", glb: "upper-body-explosion.glb" },
  ana15: { name: "right arm",     side: "surface", compartment: "motor",      info: "Upper arm — biceps/triceps motor unit.", glb: "windows_3d_viewer_flexing_arm.glb" },
  ana16: { name: "left arm",      side: "surface", compartment: "motor",      info: "Upper arm.", glb: "windows_3d_viewer_flexing_arm.glb" },
  ana17: { name: "right elbow",   side: "surface", compartment: "motor",      info: "Hinge joint, proprioception-rich.", glb: null },
  ana18: { name: "left elbow",    side: "surface", compartment: "motor",      info: "Hinge joint.", glb: null },
  ana19: { name: "right forearm", side: "surface", compartment: "motor",      info: "Forearm — grip pre-activation.", glb: null },
  ana20: { name: "left forearm",  side: "surface", compartment: "motor",      info: "Forearm.", glb: null },
  ana21: { name: "right wrist",   side: "surface", compartment: "motor",      info: "Carpal tunnel — dense sensory return.", glb: null },
  ana22: { name: "left wrist",    side: "surface", compartment: "motor",      info: "Carpal tunnel.", glb: null },
  ana23: { name: "right hand",    side: "surface", compartment: "motor",      info: "Hand — highest motor resolution in the circuit.", glb: null },
  ana24: { name: "left hand",     side: "surface", compartment: "motor",      info: "Hand.", glb: null },
  ana25: { name: "right thigh",   side: "surface", compartment: "motor",      info: "Quadriceps/hamstring. Locomotion engine.", glb: "FastRun.glb" },
  ana26: { name: "left thigh",    side: "surface", compartment: "motor",      info: "Quadriceps/hamstring.", glb: "FastRun.glb" },
  ana27: { name: "right knee",    side: "surface", compartment: "motor",      info: "Tibiofemoral joint.", glb: null },
  ana28: { name: "left knee",     side: "surface", compartment: "motor",      info: "Tibiofemoral joint.", glb: null },
  ana29: { name: "right leg",     side: "surface", compartment: "motor",      info: "Shank — soleus/gastrocnemius.", glb: "FastRun.glb" },
  ana30: { name: "left leg",      side: "surface", compartment: "motor",      info: "Shank.", glb: "FastRun.glb" },
  ana31: { name: "right ankle",   side: "surface", compartment: "motor",      info: "Ankle — primary postural pivot.", glb: "foot__ankle.glb" },
  ana32: { name: "left ankle",    side: "surface", compartment: "motor",      info: "Ankle.", glb: "foot__ankle.glb" },
  ana33: { name: "right foot",    side: "surface", compartment: "motor",      info: "Foot — ground coupling of the closed circuit.", glb: "foot__ankle.glb" },
  ana34: { name: "left foot",     side: "surface", compartment: "motor",      info: "Foot.", glb: "foot__ankle.glb" },

  // Internal regions
  ana35: { name: "brain",            side: "internal", compartment: "thought",     info: "Cortical + subcortical mass. The 17–20 W cognitive budget lives here.", glb: "bust.glb" },
  ana36: { name: "larynx",           side: "internal", compartment: "respiratory", info: "Airflow gate — cardiac-referenced rhythm coupling.", glb: null },
  ana37: { name: "thyroid",          side: "internal", compartment: "visceral",    info: "Metabolic rate modulator.", glb: null },
  ana38: { name: "trachea",          side: "internal", compartment: "respiratory", info: "Airway trunk.", glb: null },
  ana39: { name: "lungs",            side: "internal", compartment: "respiratory", info: "O₂ exchange — sets the variance-restoration rate ceiling.", glb: "thorax_and_abdomen_a_few_important_muscles.glb" },
  ana40: { name: "stomach",          side: "internal", compartment: "visceral",    info: "Upper digestive — vagal sensor.", glb: null },
  ana41: { name: "heart",            side: "internal", compartment: "cardiac",     info: "Cardiac capacitance ≈ 20 μF. Heartbeat sets f_card.", glb: null },
  ana42: { name: "spleen",           side: "internal", compartment: "visceral",    info: "Immune reservoir.", glb: null },
  ana43: { name: "liver",            side: "internal", compartment: "visceral",    info: "Metabolic hub.", glb: null },
  ana44: { name: "large intestine",  side: "internal", compartment: "visceral",    info: "Enteric nervous system — autonomic return path.", glb: null },
  ana45: { name: "small intestine",  side: "internal", compartment: "visceral",    info: "Nutrient charge gradient.", glb: null },
};

// Reverse lookup: compartment → list of region ids (so a page can
// activate a whole compartment at once).
export const COMPARTMENT_TO_REGIONS = Object.entries(REGIONS).reduce(
  (acc, [id, meta]) => {
    (acc[meta.compartment] = acc[meta.compartment] || []).push(id);
    return acc;
  },
  {}
);
