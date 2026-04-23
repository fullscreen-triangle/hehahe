/**
 * Charge-field GPU dynamics.
 *
 * The framebuffer IS the state. Each texel of the RGBA16F target holds:
 *    R = rho(x,y,t)          charge density (can be signed)
 *    G = phi(x,y,t)           potential (relaxed Poisson solution, 1 iter/frame)
 *    B = J_mag(x,y,t)         current magnitude |∇phi|, used for visualization
 *    A = coherence(x,y,t)    local Kuramoto order parameter
 *
 * The simulation uses ping-pong between two RGBA16F targets. Each frame:
 *   1) one Jacobi relaxation pass on Laplace(phi) = -rho (closed BC, no ground)
 *   2) advect rho along -∇phi (Ohm's law) with a small viscosity
 *   3) compute |J| and the local order parameter for the colour pass
 *
 * The display pass samples the state buffer and tone-maps it into the
 * bioelectric palette. There is no separate "render"; the displayed
 * frame is a readout of the computation, and the next frame reads it
 * back as input. Rendering = computing = observation.
 */

export const vertexShader = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

// Physics step: updates rho, phi, J_mag, coherence
export const stepShader = /* glsl */ `
  precision highp float;

  uniform sampler2D uState;
  uniform vec2  uRes;
  uniform float uTime;
  uniform float uDt;
  uniform vec2  uCursor;        // normalized 0..1, <0 = off
  uniform float uInject;        // charge injected by cursor
  uniform float uDiffuse;       // viscosity on rho
  uniform float uRelax;         // Poisson relaxation factor
  uniform float uDecay;         // amplitude decay (keeps closed-BC bounded)

  varying vec2 vUv;

  // Reflecting (closed, no-ground) boundary: mirror across edges.
  vec2 mirror(vec2 uv) {
    vec2 u = uv;
    if (u.x < 0.0) u.x = -u.x;
    if (u.y < 0.0) u.y = -u.y;
    if (u.x > 1.0) u.x = 2.0 - u.x;
    if (u.y > 1.0) u.y = 2.0 - u.y;
    return u;
  }

  vec4 sampleState(vec2 uv) {
    return texture2D(uState, mirror(uv));
  }

  void main() {
    vec2 px = 1.0 / uRes;
    vec4 c  = sampleState(vUv);
    vec4 l  = sampleState(vUv - vec2(px.x, 0.0));
    vec4 r  = sampleState(vUv + vec2(px.x, 0.0));
    vec4 d  = sampleState(vUv - vec2(0.0, px.y));
    vec4 u  = sampleState(vUv + vec2(0.0, px.y));

    float rho = c.r;
    float phi = c.g;

    // --- 1. Jacobi relaxation: ∇²phi = -rho  (one iteration per frame) ---
    float phiNew = 0.25 * (l.g + r.g + d.g + u.g + rho);
    phi = mix(phi, phiNew, uRelax);

    // --- 2. Current J = -∇phi  (Ohm's law in this normalised unit) ---
    vec2 J = -0.5 * vec2(r.g - l.g, u.g - d.g) / px;
    float Jmag = length(J);

    // --- 3. Advect rho along J, with diffusion and gentle decay ---
    vec2 back = vUv - J * uDt;
    float rhoAdv = sampleState(back).r;
    float lap = (l.r + r.r + d.r + u.r - 4.0 * rho);
    rho = rhoAdv + uDiffuse * lap;
    rho *= (1.0 - uDecay);

    // --- 4. Cursor injection (acts as a local intent) ---
    if (uCursor.x >= 0.0) {
      vec2 off = (vUv - uCursor) * vec2(uRes.x / uRes.y, 1.0);
      float d2 = dot(off, off);
      rho += uInject * exp(-d2 * 400.0);
    }

    // --- 5. Local order parameter (Kuramoto-like): coherence of nearby phase ---
    // Use phi gradient direction as a phase proxy.
    float theta_c = atan(J.y, J.x);
    float theta_l = atan(-0.5 * (d.g - u.g) / px.y,
                         -0.5 * (r.g - l.g) / px.x);
    float order = 0.5 + 0.5 * cos(theta_c - theta_l);

    gl_FragColor = vec4(rho, phi, Jmag, order);
  }
`;

// Display pass: tonemap the state into bioelectric colours
export const displayShader = /* glsl */ `
  precision highp float;

  uniform sampler2D uState;
  uniform float uTime;
  uniform float uIntensity;
  varying vec2 vUv;

  vec3 palette(float t) {
    // cyan -> violet -> warm amber; background is deep void.
    vec3 void0  = vec3(0.039, 0.039, 0.059);
    vec3 cyan   = vec3(0.345, 0.902, 0.851);
    vec3 violet = vec3(0.714, 0.243, 0.588);
    vec3 amber  = vec3(0.941, 0.659, 0.188);
    if (t < 0.5) {
      return mix(void0, cyan, t * 2.0);
    } else if (t < 0.85) {
      return mix(cyan, violet, (t - 0.5) / 0.35);
    }
    return mix(violet, amber, (t - 0.85) / 0.15);
  }

  void main() {
    vec4 s = texture2D(uState, vUv);
    float rho   = s.r;
    float Jmag  = s.b;
    float order = s.a;

    // Display channel = charge amplitude + current glow, modulated by coherence
    float a = abs(rho);
    float v = clamp(a * 2.0 + Jmag * 0.8, 0.0, 1.0);
    v = pow(v, 0.8) * uIntensity;

    vec3 col = palette(v);

    // Coherence pushes towards the brighter end; incoherent regions desaturate
    col = mix(col * 0.65, col, order);

    // Subtle vignette to anchor the composition
    vec2 q = vUv - 0.5;
    float vig = smoothstep(0.9, 0.2, length(q));
    col *= vig;

    gl_FragColor = vec4(col, 1.0);
  }
`;
