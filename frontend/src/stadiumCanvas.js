/**
 * 2D Stadium Canvas & Hawk-Eye Trajectory Animation Engine
 */
export class StadiumCanvasEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.cameraMode = 'full'; // 'full', 'pitch', 'hawkeye'
    
    // Ball & Delivery State
    this.animatingBall = false;
    this.ballProgress = 0;
    this.shotType = 'normal'; // 'six', 'four', 'wicket', 'dot'
    this.ballTrail = [];
    this.fireworks = [];
    
    // Animation loop
    this.lastTime = performance.now();
    this.init();
  }

  init() {
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
    requestAnimationFrame((t) => this.renderLoop(t));
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * (window.devicePixelRatio || 1);
    this.canvas.height = rect.height * (window.devicePixelRatio || 1);
    this.ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    this.width = rect.width;
    this.height = rect.height;
  }

  setCameraMode(mode) {
    this.cameraMode = mode;
  }

  triggerDelivery(shotType = 'six') {
    this.shotType = shotType;
    this.animatingBall = true;
    this.ballProgress = 0;
    this.ballTrail = [];
    
    if (shotType === 'six' || shotType === 'four') {
      this.spawnFireworks();
    }
  }

  spawnFireworks() {
    this.fireworks = [];
    const count = 35;
    const centerX = this.width / 2;
    const centerY = this.height * 0.35;
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 2 + Math.random() * 6;
      this.fireworks.push({
        x: centerX,
        y: centerY,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1.0,
        color: ['#f59e0b', '#10b981', '#3b82f6', '#f43f5e', '#8b5cf6'][Math.floor(Math.random() * 5)]
      });
    }
  }

  renderLoop(timestamp) {
    const dt = (timestamp - this.lastTime) / 1000;
    this.lastTime = timestamp;

    this.ctx.clearRect(0, 0, this.width, this.height);

    if (this.cameraMode === 'hawkeye') {
      this.drawHawkEyeView(dt);
    } else {
      this.drawFieldView(dt);
    }

    requestAnimationFrame((t) => this.renderLoop(t));
  }

  drawFieldView(dt) {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    // 1. Dark Stadium Background & Grass
    ctx.save();
    ctx.fillStyle = '#050a14';
    ctx.fillRect(0, 0, w, h);

    const isPitchZoom = this.cameraMode === 'pitch';
    const scale = isPitchZoom ? 1.6 : 1.0;
    const offsetY = isPitchZoom ? -h * 0.15 : 0;

    ctx.translate(w / 2, h / 2 + offsetY);
    ctx.scale(scale, scale);

    // Outer Grass Ellipse
    const rx = w * 0.42;
    const ry = h * 0.38;

    const grassGrad = ctx.createRadialGradient(0, 0, 10, 0, 0, rx);
    grassGrad.addColorStop(0, '#154826');
    grassGrad.addColorStop(0.7, '#0f381c');
    grassGrad.addColorStop(1, '#092411');

    ctx.beginPath();
    ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
    ctx.fillStyle = grassGrad;
    ctx.fill();

    // Concentric Mowing Stripes
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
    ctx.lineWidth = 12;
    for (let r = 30; r < rx; r += 28) {
      ctx.beginPath();
      ctx.ellipse(0, 0, r, r * (ry / rx), 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Boundary Rope (Gold Rope)
    ctx.beginPath();
    ctx.ellipse(0, 0, rx - 10, ry - 10, 0, 0, Math.PI * 2);
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 3;
    ctx.stroke();

    // 30-Yard Inner Circle
    ctx.beginPath();
    ctx.ellipse(0, 0, rx * 0.5, ry * 0.5, 0, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 6]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Pitch Rect (Dirt Color)
    const pw = 36;
    const ph = 140;
    ctx.fillStyle = '#b59265';
    ctx.fillRect(-pw / 2, -ph / 2, pw, ph);

    // Popping Crease lines
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    // Bowler crease (bottom)
    ctx.moveTo(-pw / 2 - 10, ph / 2 - 20);
    ctx.lineTo(pw / 2 + 10, ph / 2 - 20);
    // Batter crease (top)
    ctx.moveTo(-pw / 2 - 10, -ph / 2 + 20);
    ctx.lineTo(pw / 2 + 10, -ph / 2 + 20);
    ctx.stroke();

    // Wickets (Stumps)
    ctx.fillStyle = '#fef08a';
    // Top Stumps
    ctx.fillRect(-6, -ph / 2 + 10, 3, 4);
    ctx.fillRect(-1, -ph / 2 + 10, 3, 4);
    ctx.fillRect(4, -ph / 2 + 10, 3, 4);
    // Bottom Stumps
    ctx.fillRect(-6, ph / 2 - 14, 3, 4);
    ctx.fillRect(-1, ph / 2 - 14, 3, 4);
    ctx.fillRect(4, ph / 2 - 14, 3, 4);

    // Stadium Lights Effect (Glow Spots)
    this.drawStadiumLights(ctx, rx, ry);

    // Fielder dots
    this.drawFielders(ctx);

    // Ball Shot Trajectory
    if (this.animatingBall) {
      this.updateAndDrawBall(ctx, ph, rx, ry);
    }

    // Fireworks render
    this.drawFireworks(ctx);

    ctx.restore();
  }

  drawStadiumLights(ctx, rx, ry) {
    const lightPositions = [
      { x: -rx * 1.1, y: -ry * 0.9 },
      { x: rx * 1.1, y: -ry * 0.9 },
      { x: -rx * 1.1, y: ry * 0.9 },
      { x: rx * 1.1, y: ry * 0.9 }
    ];

    lightPositions.forEach(p => {
      const grad = ctx.createRadialGradient(p.x, p.y, 2, p.x, p.y, 80);
      grad.addColorStop(0, 'rgba(255, 255, 255, 0.4)');
      grad.addColorStop(0.5, 'rgba(59, 130, 246, 0.1)');
      grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 80, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  drawFielders(ctx) {
    const fielders = [
      { x: 0, y: 80, label: 'Bowler' },
      { x: 0, y: -65, label: 'Batter' },
      { x: -20, y: -80, label: 'Keeper' },
      { x: 120, y: -50, label: 'Deep Cover' },
      { x: -130, y: 30, label: 'Mid Wicket' },
      { x: 100, y: 100, label: 'Long On' },
      { x: -110, y: 110, label: 'Long Off' }
    ];

    fielders.forEach(f => {
      ctx.fillStyle = '#3b82f6';
      ctx.beginPath();
      ctx.arc(f.x, f.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });
  }

  updateAndDrawBall(ctx, pitchH, rx, ry) {
    this.ballProgress += 0.018;
    if (this.ballProgress > 1.0) {
      this.animatingBall = false;
      this.ballProgress = 1.0;
    }

    const startX = 0;
    const startY = pitchH / 2 - 20; // Bowler releasing
    const bounceX = 0;
    const bounceY = 0; // Pitch bounce point

    let targetX = 0;
    let targetY = 0;

    if (this.shotType === 'six') {
      targetX = rx * 0.75;
      targetY = -ry * 0.85;
    } else if (this.shotType === 'four') {
      targetX = -rx * 0.8;
      targetY = -ry * 0.4;
    } else if (this.shotType === 'wicket') {
      targetX = 0;
      targetY = -pitchH / 2 + 10;
    } else {
      targetX = 30;
      targetY = 20;
    }

    // Interpolate Quadratic Bezier
    const p = this.ballProgress;
    let currentX, currentY, ballZ = 0;

    if (p < 0.3) {
      // Delivery phase to pitch
      const subP = p / 0.3;
      currentX = startX + (bounceX - startX) * subP;
      currentY = startY + (bounceY - startY) * subP;
      ballZ = Math.sin(subP * Math.PI) * 15;
    } else {
      // Shot trajectory phase
      const subP = (p - 0.3) / 0.7;
      currentX = bounceX + (targetX - bounceX) * subP;
      currentY = bounceY + (targetY - bounceY) * subP;
      const maxHeight = this.shotType === 'six' ? 60 : (this.shotType === 'four' ? 20 : 5);
      ballZ = Math.sin(subP * Math.PI) * maxHeight;
    }

    // Save trail
    this.ballTrail.push({ x: currentX, y: currentY - ballZ, alpha: 1.0 });
    if (this.ballTrail.length > 15) this.ballTrail.shift();

    // Draw Trail
    this.ballTrail.forEach((t, idx) => {
      ctx.fillStyle = `rgba(245, 158, 11, ${ (idx / 15) * 0.6 })`;
      ctx.beginPath();
      ctx.arc(t.x, t.y, 2 + (idx / 15) * 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // Draw Ball Shadow & Ball
    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
    ctx.beginPath();
    ctx.arc(currentX, currentY, 4, 0, Math.PI * 2);
    ctx.fill();

    // Ball
    ctx.fillStyle = '#ef4444';
    ctx.beginPath();
    ctx.arc(currentX, currentY - ballZ, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  drawFireworks(ctx) {
    this.fireworks.forEach(f => {
      f.x += f.vx;
      f.y += f.vy;
      f.alpha -= 0.02;

      if (f.alpha > 0) {
        ctx.fillStyle = f.color;
        ctx.globalAlpha = f.alpha;
        ctx.beginPath();
        ctx.arc(f.x - this.width / 2, f.y - this.height / 2, 3, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1.0;
      }
    });
  }

  drawHawkEyeView(dt) {
    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.fillStyle = '#090d18';
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2, h / 2);

    // Hawk-Eye Grid Matrix
    ctx.strokeStyle = 'rgba(16, 185, 129, 0.2)';
    ctx.lineWidth = 1;
    for (let x = -w / 2; x < w / 2; x += 30) {
      ctx.beginPath();
      ctx.moveTo(x, -h / 2);
      ctx.lineTo(x, h / 2);
      ctx.stroke();
    }
    for (let y = -h / 2; y < h / 2; y += 30) {
      ctx.beginPath();
      ctx.moveTo(-w / 2, y);
      ctx.lineTo(w / 2, y);
      ctx.stroke();
    }

    // Pitch Corridor
    ctx.fillStyle = 'rgba(16, 185, 129, 0.08)';
    ctx.fillRect(-40, -h * 0.4, 80, h * 0.8);

    // Stumps High Def
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(-15, -h * 0.35, 6, 20);
    ctx.fillRect(-3, -h * 0.35, 6, 20);
    ctx.fillRect(9, -h * 0.35, 6, 20);

    // Animated Impact Zone Arc
    ctx.beginPath();
    ctx.arc(0, 0, 45, 0, Math.PI * 2);
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = '#10b981';
    ctx.font = '12px JetBrains Mono, monospace';
    ctx.fillText('HAWK-EYE TRAJECTORY PREDICTION', -110, -h * 0.4 + 20);
    ctx.fillText('IMPACT: IN-LINE | WICKETS: HITTING', -115, h * 0.4 - 20);

    ctx.restore();
  }
}
