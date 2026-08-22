class LinAlg {
    static magnitude(vec) {
        let ans = 0;
        for (let i = 0; i < vec.length; i++) ans += vec[i] * vec[i];
        return Math.sqrt(ans);
    }
    static add(vec1, vec2) {
        if (vec1.length != vec2.length) throw new Error('unequal dimensions');
        const vec = [];
        for (let i = 0; i < vec1.length; i++) vec.push(vec1[i] + vec2[i]);
        return vec;
    }
    static mul(scal, vec) {
        const ans = []
        for (let i = 0; i < vec.length; i++) ans.push(vec[i] * scal);
        return ans;
    }
    static subtract(vec1, vec2) {
        return LinAlg.add(vec1, LinAlg.mul(-1, vec2));
    }
    static normalise(vec1) {
        let mag = LinAlg.magnitude(vec1);
        return LinAlg.mul(1 / mag, vec1);
    }
    static dot(vec1, vec2) {
        if (vec1.length != vec2.length) throw new Error('unequal vector dimensions');
        let ans = 0;
        for (let i = 0; i < vec1.length; i++) ans += vec1[i] * vec2[i];
        return ans;
    }
    static comp(p1, p2, v1, v2) {
        return [LinAlg.dot(LinAlg.normalise(LinAlg.subtract(p2, p1)), v1), LinAlg.dot(LinAlg.normalise(LinAlg.subtract(p1, p2)), v2)];
    }
    static velocity(obj, t) {
        let ε = Math.min(1e-10,current_time_step);
        return LinAlg.mul(1 / ε, (LinAlg.subtract(obj.position(t + ε), obj.position(t))));
    }
    static find_em(t, vc, source, detector) {
        let ε = Math.min(1e-10, current_time_step);
        let α = 0.05;
        let t_b = t;
        let error = t_b + LinAlg.magnitude(LinAlg.subtract(source.position(t_b), detector.position(t))) / vc - t;
        while (error > ε) {
            error = t_b + LinAlg.magnitude(LinAlg.subtract(source.position(t_b), detector.position(t))) / vc - t;
            t_b -= α * error;
        }
        return t_b;
    }
    static zip(l1,l2){
	if(l1.length!==l2.length) throw new Error('unequal length for zip')
        const ans=[];
        for(let i=0;i<l1.length;i++) ans.push({x:l1[i],y:l2[i]});
	return ans;
    }
    static filter_zipped(l){
	const ans=[]
	for(let i=0;i<l.length;i++){
	    if(!isNaN(l[i]['x']) && !isNaN(l[i]['y'])) ans.push(l[i]);
	}
	return ans;
    }
}