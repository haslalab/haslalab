class Source{
    constructor(x,y,z,vx,vy,vz,R,ω){
        this.vx=vx;
        this.vy=vy;
        this.vz=vz;
        this.ω=ω;
        this.R=R;
        this.x=x;
        this.y=y;
        this.z=z;
    }
    render(t) {
	// draw source
        context.fillStyle = "#ff1818";
        context.beginPath();
        context.arc(canvas_width / 2 + scale * this.position(t)[0], canvas_height / 2 - scale * this.position(t)[1], source_radius, 0, 2 * Math.PI);
        context.fill();
    }
    position(t){
        return [this.x+this.vx*t+this.R*Math.cos(this.ω*t),this.y+this.vy*t+this.R*Math.sin(this.ω*t),this.z+this.vz*t];
    }
    velocity(t) {
        return [this.vx - this.ω * this.R * Math.sin(this.ω * t), this.vy + this.ω * this.R * Math.cos(this.ω * t),this.vz]
    }
}