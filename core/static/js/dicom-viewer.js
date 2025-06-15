// Classe pour gérer le visualiseur DICOM
class DicomViewer {
    constructor(config) {
        this.config = config;
        this.currentIndex = 0;
        this.instances = config.instances || [];
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        this.windowWidth = 400;
        this.windowCenter = 40;
        this.measurements = [];
        this.currentTool = 'pan';
        
        this.canvas = null;
        this.ctx = null;
        this.image = new Image();
        
        this.init();
    }
    
    init() {
        // Créer le canvas si nécessaire
        this.setupCanvas();
        this.setupEventListeners();
        this.loadImage(0);
    }
    
    setupCanvas() {
        // Si on veut utiliser un canvas au lieu d'une image simple
        const container = document.getElementById('viewerCanvas');
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'dicomCanvas';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        container.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');
        
        // Ajuster la taille du canvas
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }
    
    resizeCanvas() {
        const container = this.canvas.parentElement;
        this.canvas.width = container.clientWidth;
        this.canvas.height = container.clientHeight;
        this.render();
    }
    
    loadImage(index) {
        if (index < 0 || index >= this.instances.length) return;
        
        this.currentIndex = index;
        const instanceId = this.instances[index];
        
        this.showLoading(true);
        
        this.image.onload = () => {
            this.showLoading(false);
            this.render();
            this.updateUI();
        };
        
        this.image.onerror = () => {
            this.showLoading(false);
            console.error('Erreur de chargement de l\'image');
        };
        
        this.image.src = `/viewer/api/instances/${instanceId}/full_image/`;
    }
    
    render() {
        if (!this.ctx || !this.image.complete) return;
        
        // Effacer le canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Sauvegarder le contexte
        this.ctx.save();
        
        // Appliquer les transformations
        this.ctx.translate(this.canvas.width / 2, this.canvas.height / 2);
        this.ctx.scale(this.zoom, this.zoom);
        this.ctx.translate(this.panX, this.panY);
        
        // Dessiner l'image centrée
        this.ctx.drawImage(
            this.image,
            -this.image.width / 2,
            -this.image.height / 2
        );
        
        // Restaurer le contexte
        this.ctx.restore();
        
        // Dessiner les mesures
        this.drawMeasurements();
        
        // Dessiner les informations
        this.drawInfo();
    }
    
    drawMeasurements() {
        this.ctx.save();
        this.ctx.strokeStyle = '#00ff00';
        this.ctx.lineWidth = 2;
        this.ctx.font = '14px Arial';
        this.ctx.fillStyle = '#00ff00';
        
        this.measurements.forEach(measurement => {
            this.ctx.beginPath();
            this.ctx.moveTo(measurement.start.x, measurement.start.y);
            this.ctx.lineTo(measurement.end.x, measurement.end.y);
            this.ctx.stroke();
            
            // Afficher la distance
            const distance = this.calculateDistance(measurement.start, measurement.end);
            const midX = (measurement.start.x + measurement.end.x) / 2;
            const midY = (measurement.start.y + measurement.end.y) / 2;
            this.ctx.fillText(`${distance.toFixed(1)} mm`, midX, midY - 5);
        });
        
        this.ctx.restore();
    }
    
    drawInfo() {
        this.ctx.save();
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(10, 10, 200, 100);
        
        this.ctx.fillStyle = 'white';
        this.ctx.font = '14px Arial';
        this.ctx.fillText(`Image: ${this.currentIndex + 1}/${this.instances.length}`, 20, 30);
        this.ctx.fillText(`Zoom: ${(this.zoom * 100).toFixed(0)}%`, 20, 50);
        this.ctx.fillText(`W/C: ${this.windowWidth}/${this.windowCenter}`, 20, 70);
        this.ctx.fillText(`Tool: ${this.currentTool}`, 20, 90);
        
        this.ctx.restore();
    }
    
    calculateDistance(point1, point2) {
        const dx = point2.x - point1.x;
        const dy = point2.y - point1.y;
        return Math.sqrt(dx * dx + dy * dy) * 0.5; // Conversion approximative en mm
    }
    
    setupEventListeners() {
        // Gestion de la souris
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e));
        
        // Gestion du clavier
        document.addEventListener('keydown', (e) => this.onKeyDown(e));
    }
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.isMouseDown = true;
        this.lastMouseX = x;
        this.lastMouseY = y;
        
        if (this.currentTool === 'measure') {
            this.startMeasurement = { x, y };
        }
    }
    
    onMouseMove(e) {
        if (!this.isMouseDown) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const dx = x - this.lastMouseX;
        const dy = y - this.lastMouseY;
        
        if (this.currentTool === 'pan') {
            this.panX += dx / this.zoom;
            this.panY += dy / this.zoom;
            this.render();
        } else if (this.currentTool === 'window') {
            this.windowWidth += dx;
            this.windowCenter += dy;
            this.applyWindowing();
        }
        
        this.lastMouseX = x;
        this.lastMouseY = y;
    }
    
    onMouseUp(e) {
        if (this.currentTool === 'measure' && this.startMeasurement) {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            this.measurements.push({
                start: this.startMeasurement,
                end: { x, y }
            });
            
            this.render();
        }
        
        this.isMouseDown = false;
        this.startMeasurement = null;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        this.zoom = Math.max(0.1, Math.min(5, this.zoom * delta));
        this.render();
    }
    
    onKeyDown(e) {
        switch(e.key) {
            case 'ArrowLeft':
                this.previousImage();
                break;
            case 'ArrowRight':
                this.nextImage();
                break;
            case 'r':
                this.reset();
                break;
            case 'Delete':
                this.clearMeasurements();
                break;
        }
    }
    
    setTool(tool) {
        this.currentTool = tool;
        this.updateUI();
    }
    
    previousImage() {
        if (this.currentIndex > 0) {
            this.loadImage(this.currentIndex - 1);
        }
    }
    
    nextImage() {
        if (this.currentIndex < this.instances.length - 1) {
            this.loadImage(this.currentIndex + 1);
        }
    }
    
    reset() {
        this.zoom = 1;
        this.panX = 0;
        this.panY = 0;
        this.windowWidth = 400;
        this.windowCenter = 40;
        this.clearMeasurements();
        this.render();
    }
    
    clearMeasurements() {
        this.measurements = [];
        this.render();
    }
    
    applyWindowing() {
        // Implémenter le fenêtrage DICOM
        // Ceci nécessiterait de travailler avec les données DICOM brutes
        console.log(`Window: ${this.windowWidth}, Center: ${this.windowCenter}`);
    }
    
    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) {
            spinner.style.display = show ? 'block' : 'none';
        }
    }
    
    updateUI() {
        // Mettre à jour l'interface utilisateur
        const currentImageEl = document.getElementById('currentImage');
        if (currentImageEl) {
            currentImageEl.textContent = this.currentIndex + 1;
        }
        
        const zoomLevelEl = document.getElementById('zoomLevel');
        if (zoomLevelEl) {
            zoomLevelEl.textContent = `${(this.zoom * 100).toFixed(0)}%`;
        }
    }
}

// Initialiser le visualiseur quand le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    if (window.dicomViewerConfig) {
        window.dicomViewer = new DicomViewer(window.dicomViewerConfig);
    }
});