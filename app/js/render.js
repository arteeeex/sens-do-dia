// Desenho da cena por raio (WebGL2): ceu/chao com grade em graus e o alvo (cabeca + corpo).
// A projecao e a do CS2: FOV vertical fixo (tan = 0,75) e horizontal pelo formato da imagem.
(function (global) {
  'use strict';

  const VS = `#version 300 es
in vec2 p;
void main() { gl_Position = vec4(p, 0.0, 1.0); }`;

  const FS = `#version 300 es
precision highp float;
uniform vec2 uRes;
uniform vec3 uF, uR, uU;
uniform vec2 uTan;
uniform vec3 uC;      // centro da cabeca (olho do jogador na origem)
uniform vec3 uRad;    // semi-eixos da cabeca (esfera oficial do CS2: raio 5)
uniform vec4 uCa[16]; // capsulas do corpo (hitboxes do CS2): ponta a + raio
uniform vec4 uCb[16]; // ponta b
uniform int uNc;
uniform vec4 uBs;     // esfera que envolve o boneco (pula o teste fora dela)
uniform float uShow;
uniform float uFlash; // 0..1: brilho rapido quando mata
out vec4 o;

vec3 raio(vec2 frag) {
  vec2 ndc = frag / uRes * 2.0 - 1.0;
  return normalize(uF + ndc.x * uTan.x * uR + ndc.y * uTan.y * uU);
}

float hitEll(vec3 rd, vec3 c, vec3 r) {
  vec3 oo = (-c) / r;
  vec3 d = rd / r;
  float a = dot(d, d), b = dot(oo, d), cc = dot(oo, oo) - 1.0;
  float h = b * b - a * cc;
  if (h < 0.0) return -1.0;
  return (-b - sqrt(h)) / a;
}

float hitCap(vec3 rd, vec3 pa, vec3 pb, float ra) {
  vec3 ro = vec3(0.0);
  vec3 ba = pb - pa, oa = ro - pa;
  float baba = dot(ba, ba), bard = dot(ba, rd), baoa = dot(ba, oa);
  if (baba < 1e-6) {                 // capsula sem comprimento = esfera
    float b0 = dot(rd, oa), c0 = dot(oa, oa) - ra * ra, h0 = b0 * b0 - c0;
    return h0 > 0.0 ? -b0 - sqrt(h0) : -1.0;
  }
  float rdoa = dot(rd, oa), oaoa = dot(oa, oa);
  float a = baba - bard * bard;
  float b = baba * rdoa - baoa * bard;
  float c = baba * oaoa - baoa * baoa - ra * ra * baba;
  float h = b * b - a * c;
  if (h >= 0.0) {
    float t = (-b - sqrt(h)) / a;
    float y = baoa + t * bard;
    if (y > 0.0 && y < baba) return t;
    vec3 oc = (y <= 0.0) ? oa : ro - pb;
    b = dot(rd, oc);
    c = dot(oc, oc) - ra * ra;
    h = b * b - c;
    if (h > 0.0) return -b - sqrt(h);
  }
  return -1.0;
}

vec3 fundo(vec3 rd) {
  float dp = degrees(asin(clamp(-rd.y, -1.0, 1.0)));   // + = abaixo do horizonte
  float dy = degrees(atan(rd.x, rd.z));
  vec3 col = dp < 0.0
    ? mix(vec3(0.24, 0.26, 0.30), vec3(0.13, 0.15, 0.19), clamp(-dp / 70.0, 0.0, 1.0))
    : mix(vec3(0.21, 0.20, 0.18), vec3(0.08, 0.08, 0.08), clamp(dp / 70.0, 0.0, 1.0));
  float fy = max(fwidth(dy), 1e-4), fp = max(fwidth(dp), 1e-4);
  float polo = 1.0 - smoothstep(55.0, 80.0, abs(dp));
  float my = abs(fract(dy / 5.0 + 0.5) - 0.5) * 5.0;
  float mp = abs(fract(dp / 5.0 + 0.5) - 0.5) * 5.0;
  float My = abs(fract(dy / 45.0 + 0.5) - 0.5) * 45.0;
  float Mp = abs(fract(dp / 15.0 + 0.5) - 0.5) * 15.0;
  float fino = max((1.0 - smoothstep(0.0, fy * 1.2, my)) * polo, 1.0 - smoothstep(0.0, fp * 1.2, mp));
  float grosso = max((1.0 - smoothstep(0.0, fy * 1.8, My)) * polo, 1.0 - smoothstep(0.0, fp * 1.8, Mp));
  col += vec3(0.055) * fino + vec3(0.07) * grosso;
  float hz = 1.0 - smoothstep(0.0, fp * 1.6, abs(dp));
  col = mix(col, vec3(0.50, 0.52, 0.55), hz * 0.85);
  return col;
}

vec3 luz(vec3 n, vec3 base) {
  vec3 l = normalize(vec3(0.35, 0.85, -0.4));
  float dif = max(dot(n, l), 0.0);
  return base * (0.38 + 0.70 * dif);
}

void main() {
  vec3 rd = raio(gl_FragCoord.xy);
  vec3 col = fundo(rd);
  if (uShow > 0.5) {
    vec3 acc = vec3(0.0);
    float cob = 0.0;
    const vec2 OFF[4] = vec2[4](vec2(0.125, 0.375), vec2(0.375, -0.125), vec2(-0.125, -0.375), vec2(-0.375, 0.125));
    const vec3 MASSINHA = vec3(0.84, 0.64, 0.48);
    for (int i = 0; i < 4; i++) {
      vec3 r = raio(gl_FragCoord.xy + OFF[i]);
      float melhor = 1e9;
      vec3 n = vec3(0.0);
      float th = hitEll(r, uC, uRad);
      if (th > 0.0) { melhor = th; n = normalize((r * th - uC) / (uRad * uRad)); }
      float bb = dot(r, uBs.xyz);
      if (bb * bb - dot(uBs.xyz, uBs.xyz) + uBs.w * uBs.w > 0.0) {
        for (int k = 0; k < 16; k++) {
          if (k >= uNc) break;
          float t = hitCap(r, uCa[k].xyz, uCb[k].xyz, uCa[k].w);
          if (t > 0.0 && t < melhor) {
            melhor = t;
            vec3 p = r * t;
            vec3 ba = uCb[k].xyz - uCa[k].xyz;
            float h = clamp(dot(p - uCa[k].xyz, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
            n = normalize(p - (uCa[k].xyz + h * ba));
          }
        }
      }
      if (melhor < 1e8) {
        acc += mix(luz(n, MASSINHA), vec3(1.0), uFlash);
        cob += 1.0;
      }
    }
    if (cob > 0.0) col = mix(col, acc / cob, cob / 4.0);
  }
  o = vec4(col, 1.0);
}`;

  function compilar(gl, tipo, src) {
    const s = gl.createShader(tipo);
    gl.shaderSource(s, src);
    gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
      throw new Error('shader: ' + gl.getShaderInfoLog(s));
    }
    return s;
  }

  function criar(canvas) {
    const gl = canvas.getContext('webgl2', { antialias: false, alpha: false, depth: false,
      desynchronized: true, powerPreference: 'high-performance', preserveDrawingBuffer: false });
    if (!gl) throw new Error('WebGL2 indisponivel neste navegador.');
    const prog = gl.createProgram();
    gl.attachShader(prog, compilar(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(prog, compilar(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(prog));
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const u = {};
    ['uRes', 'uF', 'uR', 'uU', 'uTan', 'uC', 'uRad', 'uCa', 'uCb', 'uNc', 'uBs', 'uShow', 'uFlash'].forEach((n) => {
      u[n] = gl.getUniformLocation(prog, n);
    });
    return {
      desenhar(cena) {
        const w = canvas.width, h = canvas.height;
        gl.viewport(0, 0, w, h);
        gl.uniform2f(u.uRes, w, h);
        gl.uniform3fv(u.uF, cena.f);
        gl.uniform3fv(u.uR, cena.r);
        gl.uniform3fv(u.uU, cena.u);
        gl.uniform2f(u.uTan, cena.tanH, cena.tanV);
        gl.uniform1f(u.uShow, cena.alvo ? 1 : 0);
        gl.uniform1f(u.uFlash, cena.flash || 0);
        if (cena.alvo) {
          gl.uniform3fv(u.uC, cena.alvo.c);
          gl.uniform3fv(u.uRad, cena.alvo.rad);
          gl.uniform4fv(u.uCa, cena.alvo.ca);
          gl.uniform4fv(u.uCb, cena.alvo.cb);
          gl.uniform1i(u.uNc, cena.alvo.nc);
          gl.uniform4fv(u.uBs, cena.alvo.bs);
        }
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      },
    };
  }

  global.Render = { criar };
})(window);
