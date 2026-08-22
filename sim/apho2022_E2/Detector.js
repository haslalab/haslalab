class Detector {
    constructor(x, y, z, vx, vy, vz) {
        this.vx = vx;
        this.vy = vy;
        this.vz = vz;
        this.x = x;
        this.y = y;
        this.z = z;
    }
    position(t) {
        return [this.x + this.vx * t, this.y + this.vy * t, this.z + this.vz * t];
    }
    velocity(t) {
        return [this.vx, this.vy, this.vz];
    }
    render(t) {
        context.fillStyle = "#1f51ff";
        context.beginPath();
        context.arc(canvas_width / 2 + scale * this.position(t)[0], canvas_height / 2 - this.position(t)[1], detector_radius, 0, 2 * Math.PI);
        context.fill();
    }
}