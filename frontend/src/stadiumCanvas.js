/**
 * Transparent broadcast-animation layer for the Pomona stadium artwork.
 * The generated venue panorama remains the visual base; this canvas adds
 * live trajectory, crowd sparkle, broadcast scanning, and Hawk-Eye mode.
 */
export class StadiumCanvasEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas?.getContext('2d');
    this.stage = this.canvas?.closest('.stadium-visual');
    this.cameraMode = 'full';
    this.animatingBall = false;
    this.ballProgress = 0;
    this.shotType = 'six';
    this.ballTrail = [];
    this.fireworks = [];
    this.sparkles = this.createSparkles(78);
    this.lastTime = performance.now();
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    requestAnimationFrame((time) => this.renderLoop(time));
  }

  createSparkles(count) {
    let seed = 20280714;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };
    return Array.from({ length: count }, () => ({
      x: random(),
      y: 0.58 + random() * 0.32,
      phase: random() * Math.PI * 2,
      size: 0.5 + random() * 1.7,
      speed: 0.55 + random() * 1.4,
    }));
  }

  resizeCanvas() {
    if (!this.canvas || !this.ctx) return;
    const rect = this.canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = Math.max(1, Math.round(rect.width * ratio));
    this.canvas.height = Math.max(1, Math.round(rect.height * ratio));
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.width = rect.width;
    this.height = rect.height;
  }

  setCameraMode(mode) {
    this.cameraMode = mode;
    if (this.stage) this.stage.dataset.camera = mode;
  }

  triggerDelivery(shotType = 'six') {
    this.shotType = shotType;
    this.animatingBall = true;
    this.ballProgress = 0;
    this.ballTrail = [];
    if (shotType === 'six' || shotType === 'four') this.spawnFireworks();
  }

  spawnFireworks() {
    const palettes = ['#ffb25f', '#ff6846', '#64e6eb', '#bc7cff', '#91f2a5'];
    const centers = [
      { x: this.width * 0.25, y: this.height * 0.34 },
      { x: this.width * 0.76, y: this.height * 0.3 },
    ];
    this.fireworks = centers.flatMap((center, burstIndex) =>
      Array.from({ length: 30 }, (_, index) => {
        const angle = (Math.PI * 2 * index) / 30 + burstIndex * 0.17;
        const speed = 26 + (index % 7) * 7;
        return {
          x: center.x,
          y: center.y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: 1,
          color: palettes[(index + burstIndex) % palettes.length],
        };
      }),
    );
  }

  renderLoop(timestamp) {
    if (!this.ctx) return;
    const delta = Math.min((timestamp - this.lastTime) / 1000, 0.05);
    this.lastTime = timestamp;
    this.ctx.clearRect(0, 0, this.width, this.height);

    if (this.cameraMode === 'hawkeye') {
      this.drawHawkEye(timestamp);
    } else {
      this.drawBroadcastAtmosphere(timestamp);
    }

    if (this.animatingBall) this.updateAndDrawBall(delta);
    this.drawFireworks(delta);
    requestAnimationFrame((time) => this.renderLoop(time));
  }

  drawBroadcastAtmosphere(timestamp) {
    const ctx = this.ctx;
    const t = timestamp / 1000;

    const sweepX = ((t * 42) % (this.width + 180)) - 90;
    const sweep = ctx.createLinearGradient(sweepX - 70, 0, sweepX + 70, 0);
    sweep.addColorStop(0, 'rgba(255,255,255,0)');
    sweep.addColorStop(0.5, 'rgba(255,210,155,0.055)');
    sweep.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = sweep;
    ctx.fillRect(0, 0, this.width, this.height);

    this.sparkles.forEach((sparkle) => {
      const alpha = 0.12 + Math.max(0, Math.sin(t * sparkle.speed + sparkle.phase)) * 0.58;
      ctx.fillStyle = `rgba(255, 201, 126, ${alpha})`;
      ctx.beginPath();
      ctx.arc(
        sparkle.x * this.width,
        sparkle.y * this.height,
        sparkle.size,
        0,
        Math.PI * 2,
      );
      ctx.fill();
    });

    const sunGlow = ctx.createRadialGradient(
      this.width * 0.9,
      this.height * 0.06,
      0,
      this.width * 0.9,
      this.height * 0.06,
      this.width * 0.3,
    );
    sunGlow.addColorStop(0, 'rgba(255, 197, 122, 0.14)');
    sunGlow.addColorStop(1, 'rgba(255, 197, 122, 0)');
    ctx.fillStyle = sunGlow;
    ctx.fillRect(0, 0, this.width, this.height);
  }

  drawHawkEye(timestamp) {
    const ctx = this.ctx;
    const t = timestamp / 1000;
    ctx.fillStyle = 'rgba(2, 12, 17, 0.46)';
    ctx.fillRect(0, 0, this.width, this.height);

    ctx.save();
    ctx.strokeStyle = 'rgba(100, 230, 235, 0.18)';
    ctx.lineWidth = 1;
    const spacing = Math.max(28, this.width / 24);
    for (let x = 0; x <= this.width; x += spacing) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.height);
      ctx.stroke();
    }
    for (let y = 0; y <= this.height; y += spacing) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
      ctx.stroke();
    }

    const pitchX = this.width * 0.5;
    const pitchY = this.height * 0.58;
    const pulse = 46 + Math.sin(t * 3) * 8;
    ctx.strokeStyle = '#64e6eb';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(pitchX, pitchY, pulse, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(255, 178, 95, 0.7)';
    ctx.strokeRect(pitchX - 26, pitchY - 94, 52, 188);

    ctx.fillStyle = '#64e6eb';
    ctx.font = '600 10px "JetBrains Mono", monospace';
    ctx.fillText('TRAJECTORY LAB / LIVE SIM', 22, this.height - 92);
    ctx.fillStyle = 'rgba(246,244,236,.76)';
    ctx.fillText('PITCH VECTOR  88.4 KM/H', 22, this.height - 72);
    ctx.fillText('IMPACT ZONE   IN-LINE', 22, this.height - 54);
    ctx.fillText('CONFIDENCE    94.7%', 22, this.height - 36);
    ctx.restore();
  }

  updateAndDrawBall(delta) {
    this.ballProgress = Math.min(1, this.ballProgress + delta * 0.62);
    if (this.ballProgress >= 1) this.animatingBall = false;

    const start = { x: this.width * 0.5, y: this.height * 0.69 };
    const impact = { x: this.width * 0.5, y: this.height * 0.57 };
    const targets = {
      six: { x: this.width * 0.78, y: this.height * 0.27, lift: this.height * 0.24 },
      four: { x: this.width * 0.17, y: this.height * 0.55, lift: this.height * 0.09 },
      wicket: { x: this.width * 0.5, y: this.height * 0.49, lift: this.height * 0.035 },
      dot: { x: this.width * 0.54, y: this.height * 0.59, lift: this.height * 0.02 },
    };
    const target = targets[this.shotType] || targets.dot;
    const p = this.ballProgress;
    let x;
    let y;

    if (p < 0.34) {
      const sub = p / 0.34;
      x = start.x + (impact.x - start.x) * sub;
      y = start.y + (impact.y - start.y) * sub - Math.sin(sub * Math.PI) * 18;
    } else {
      const sub = (p - 0.34) / 0.66;
      x = impact.x + (target.x - impact.x) * sub;
      y = impact.y + (target.y - impact.y) * sub - Math.sin(sub * Math.PI) * target.lift;
    }

    this.ballTrail.push({ x, y });
    if (this.ballTrail.length > 22) this.ballTrail.shift();
    this.ballTrail.forEach((point, index) => {
      const progress = (index + 1) / this.ballTrail.length;
      this.ctx.fillStyle = `rgba(255, 178, 95, ${progress * 0.72})`;
      this.ctx.beginPath();
      this.ctx.arc(point.x, point.y, 1 + progress * 3.4, 0, Math.PI * 2);
      this.ctx.fill();
    });

    const glow = this.ctx.createRadialGradient(x, y, 0, x, y, 20);
    glow.addColorStop(0, 'rgba(255,255,255,.95)');
    glow.addColorStop(0.22, 'rgba(255,104,70,.9)');
    glow.addColorStop(1, 'rgba(255,104,70,0)');
    this.ctx.fillStyle = glow;
    this.ctx.beginPath();
    this.ctx.arc(x, y, 20, 0, Math.PI * 2);
    this.ctx.fill();
  }

  drawFireworks(delta) {
    this.fireworks = this.fireworks.filter((particle) => particle.life > 0);
    this.fireworks.forEach((particle) => {
      particle.x += particle.vx * delta;
      particle.y += particle.vy * delta;
      particle.vy += 23 * delta;
      particle.life -= delta * 0.7;
      this.ctx.globalAlpha = Math.max(0, particle.life);
      this.ctx.fillStyle = particle.color;
      this.ctx.beginPath();
      this.ctx.arc(particle.x, particle.y, 1.2, 0, Math.PI * 2);
      this.ctx.fill();
    });
    this.ctx.globalAlpha = 1;
  }
}
