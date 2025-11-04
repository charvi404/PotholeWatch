import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { MapPin, Shield, TrendingUp, Users } from 'lucide-react';

const Landing = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-md border-b border-gray-200 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <Shield className="w-8 h-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">PotholeWatch</span>
            </div>
            <Button 
              onClick={() => navigate('/auth')}
              variant="outline"
              data-testid="nav-login-btn"
            >
              Login
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="pt-32 pb-20 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 mb-6">
              Smart Pothole Detection for
              <span className="text-blue-600"> Pune</span>
            </h1>
            <p className="text-lg sm:text-xl text-gray-600 mb-8">
              AI-powered pothole detection and reporting system. Upload images, get instant analysis, 
              and help make our roads safer for everyone.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                size="lg" 
                className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-6 text-lg rounded-full"
                onClick={() => navigate('/auth')}
                data-testid="hero-get-started-btn"
              >
                <MapPin className="w-5 h-5 mr-2" />
                Report a Pothole
              </Button>
              <Button 
                size="lg" 
                variant="outline"
                className="px-8 py-6 text-lg rounded-full"
                onClick={() => navigate('/auth')}
                data-testid="hero-authority-login-btn"
              >
                Authority Login
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-16">How It Works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MapPin className="w-8 h-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Upload & Locate</h3>
              <p className="text-gray-600">Snap a photo and auto-detect location or enter address manually</p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">AI Analysis</h3>
              <p className="text-gray-600">Get instant severity assessment, area calculation, and cost estimates</p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-purple-600" />
              </div>
              <h3 className="text-xl font-bold mb-2">Track & Resolve</h3>
              <p className="text-gray-600">Authorities receive SMS alerts and track repair progress in real-time</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="py-20 bg-gradient-to-r from-blue-600 to-blue-700">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8 text-center text-white">
            <div>
              <div className="text-4xl font-bold mb-2">AI-Powered</div>
              <p className="text-blue-100">YOLOv8 Detection Model</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">Real-time</div>
              <p className="text-blue-100">SMS Notifications</p>
            </div>
            <div>
              <div className="text-4xl font-bold mb-2">Accurate</div>
              <p className="text-blue-100">Area & Cost Estimation</p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Shield className="w-6 h-6 text-blue-400" />
            <span className="text-lg font-bold text-white">PotholeWatch Pune</span>
          </div>
          <p className="text-sm">Making roads safer, one pothole at a time</p>
          <p className="text-xs mt-4 text-gray-500">© 2025 Smart Pothole Detection System</p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
