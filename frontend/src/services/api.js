import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const api = {
  // Auth
  signup: async (name, email, password, role) => {
    const response = await axios.post(`${API}/auth/signup`, {
      name,
      email,
      password,
      role
    });
    return response.data;
  },

  login: async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, {
      email,
      password
    });
    return response.data;
  },

  // Pothole operations
  analyzePothole: async (file, location, coordinates, distanceFactor = 1.0) => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('location', location);
    formData.append('coordinates', JSON.stringify(coordinates))
    formData.append('distance_factor', distanceFactor);
;

    const response = await axios.post(`${API}/potholes/analyze`, formData, {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data;
  },

  getAllPotholes: async (status = null, severity = null) => {
    const params = {};
    if (status) params.status = status;
    if (severity) params.severity = severity;

    const response = await axios.get(`${API}/potholes`, {
      headers: getAuthHeader(),
      params
    });
    return response.data;
  },

  getPothole: async (id) => {
    const response = await axios.get(`${API}/potholes/${id}`, {
      headers: getAuthHeader()
    });
    return response.data;
  },

  notifyAuthorities: async (potholeId) => {
    const response = await axios.post(
      `${API}/potholes/${potholeId}/notify`,
      {},
      { headers: getAuthHeader() }
    );
    return response.data;
  },

  potholeAction: async (potholeId, action, notes = null) => {
    const response = await axios.post(
      `${API}/potholes/${potholeId}/action`,
      { action, notes },
      { headers: getAuthHeader() }
    );
    return response.data;
  },

  getUserReports: async (userId) => {
    const response = await axios.get(`${API}/users/${userId}/reports`, {
      headers: getAuthHeader()
    });
    return response.data;
  },
assignDrone: async (potholeId) => {
  const response = await axios.post(
    `${API}/potholes/${potholeId}/assign-drone`,
    {},
    { headers: getAuthHeader() }
  );
  return response.data;
},


  getNotifications: async () => {
    const response = await axios.get(`${API}/notifications`, {
      headers: getAuthHeader()
    });
    return response.data;
  }
};

export default api;
