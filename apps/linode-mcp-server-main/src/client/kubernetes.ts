import { AxiosInstance } from 'axios';
import { PaginatedResponse, PaginationParams } from './instances';

// Kubernetes cluster interfaces
export interface KubernetesCluster {
  id: number;
  label: string;
  k8s_version: string;
  region: string;
  status: 'ready' | 'not_ready' | 'provisioning' | 'deleted' | 'updating' | 'upgrading';
  created: string;
  updated: string;
  tags: string[];
  control_plane: {
    high_availability: boolean;
  };
}

// Kubernetes node pool interfaces
export interface KubernetesNodePool {
  id: number;
  count: number;
  type: string;
  tags: string[];
  autoscaler?: {
    enabled: boolean;
    min?: number;
    max?: number;
  };
  nodes: KubernetesNode[];
}

export interface KubernetesNode {
  id: string;
  instance_id: number;
  status: 'ready' | 'not_ready' | 'provisioning';
}

// Kubernetes version interfaces
export interface KubernetesVersion {
  id: string;
}

// Kubernetes API endpoint interfaces
export interface KubeConfig {
  kubeconfig: string;
}

export interface APIEndpoint {
  endpoint: string;
}

export interface KubernetesDashboard {
  url: string;
}

export interface KubernetesType {
  id: string;
  label: string;
  price: {
    monthly: number;
    hourly: number;
  };
  region_prices?: Record<string, {
    monthly: number;
    hourly: number;
  }>;
}

// Request interfaces
export interface CreateKubernetesClusterRequest {
  label: string;
  region: string;
  k8s_version: string;
  tags?: string[];
  node_pools: {
    type: string;
    count: number;
    tags?: string[];
    autoscaler?: {
      enabled: boolean;
      min?: number;
      max?: number;
    };
  }[];
  control_plane?: {
    high_availability?: boolean;
  };
}

export interface UpdateKubernetesClusterRequest {
  label?: string;
  k8s_version?: string;
  tags?: string[];
  control_plane?: {
    high_availability?: boolean;
  };
}

export interface CreateNodePoolRequest {
  type: string;
  count: number;
  tags?: string[];
  autoscaler?: {
    enabled: boolean;
    min?: number;
    max?: number;
  };
}

export interface UpdateNodePoolRequest {
  count?: number;
  tags?: string[];
  autoscaler?: {
    enabled: boolean;
    min?: number;
    max?: number;
  };
}

export interface RecycleNodePoolRequest {
  nodes: string[];
}

// Client interface
export interface KubernetesClient {
  // Cluster operations
  getClusters: (params?: PaginationParams) => Promise<PaginatedResponse<KubernetesCluster>>;
  getCluster: (id: number) => Promise<KubernetesCluster>;
  createCluster: (data: CreateKubernetesClusterRequest) => Promise<KubernetesCluster>;
  updateCluster: (id: number, data: UpdateKubernetesClusterRequest) => Promise<KubernetesCluster>;
  deleteCluster: (id: number) => Promise<void>;
  recycleCluster: (id: number) => Promise<void>;
  upgradeCluster: (id: number) => Promise<void>;
  
  // Node pool operations
  getNodePools: (clusterId: number) => Promise<KubernetesNodePool[]>;
  getNodePool: (clusterId: number, poolId: number) => Promise<KubernetesNodePool>;
  createNodePool: (clusterId: number, data: CreateNodePoolRequest) => Promise<KubernetesNodePool>;
  updateNodePool: (clusterId: number, poolId: number, data: UpdateNodePoolRequest) => Promise<KubernetesNodePool>;
  deleteNodePool: (clusterId: number, poolId: number) => Promise<void>;
  recycleNodes: (clusterId: number, poolId: number, data: RecycleNodePoolRequest) => Promise<void>;
  
  // Node operations
  deleteNode: (clusterId: number, nodeId: string) => Promise<void>;
  recycleNode: (clusterId: number, nodeId: string) => Promise<void>;
  
  // Cluster access 
  getKubeconfig: (id: number) => Promise<KubeConfig>;
  getAPIEndpoints: (id: number) => Promise<APIEndpoint[]>;
  getDashboardURL: (id: number) => Promise<KubernetesDashboard>;
  deleteServiceToken: (id: number) => Promise<void>;
  
  // Version and type information
  getVersions: () => Promise<KubernetesVersion[]>;
  getVersion: (version: string) => Promise<KubernetesVersion>;
  getTypes: () => Promise<KubernetesType[]>;
}

/**
 * Creates a Kubernetes (LKE) client for interfacing with the Linode Kubernetes Engine API
 */
export function createKubernetesClient(axios: AxiosInstance): KubernetesClient {
  return {
    // Cluster operations
    getClusters: async (params?: PaginationParams) => {
      const response = await axios.get('/lke/clusters', { params });
      return response.data;
    },
    getCluster: async (id: number) => {
      const response = await axios.get(`/lke/clusters/${id}`);
      return response.data;
    },
    createCluster: async (data: CreateKubernetesClusterRequest) => {
      const response = await axios.post('/lke/clusters', data);
      return response.data;
    },
    updateCluster: async (id: number, data: UpdateKubernetesClusterRequest) => {
      const response = await axios.put(`/lke/clusters/${id}`, data);
      return response.data;
    },
    deleteCluster: async (id: number) => {
      await axios.delete(`/lke/clusters/${id}`);
    },
    recycleCluster: async (id: number) => {
      await axios.post(`/lke/clusters/${id}/recycle`);
    },
    upgradeCluster: async (id: number) => {
      await axios.post(`/lke/clusters/${id}/upgrade`);
    },
    
    // Node pool operations
    getNodePools: async (clusterId: number) => {
      const response = await axios.get(`/lke/clusters/${clusterId}/pools`);
      // Linode API returns node pools as a paginated response, so extract the data array
      return response.data.data;
    },
    getNodePool: async (clusterId: number, poolId: number) => {
      const response = await axios.get(`/lke/clusters/${clusterId}/pools/${poolId}`);
      return response.data;
    },
    createNodePool: async (clusterId: number, data: CreateNodePoolRequest) => {
      const response = await axios.post(`/lke/clusters/${clusterId}/pools`, data);
      return response.data;
    },
    updateNodePool: async (clusterId: number, poolId: number, data: UpdateNodePoolRequest) => {
      const response = await axios.put(`/lke/clusters/${clusterId}/pools/${poolId}`, data);
      return response.data;
    },
    deleteNodePool: async (clusterId: number, poolId: number) => {
      await axios.delete(`/lke/clusters/${clusterId}/pools/${poolId}`);
    },
    recycleNodes: async (clusterId: number, poolId: number, data: RecycleNodePoolRequest) => {
      await axios.post(`/lke/clusters/${clusterId}/pools/${poolId}/recycle`, data);
    },
    
    // Node operations
    deleteNode: async (clusterId: number, nodeId: string) => {
      await axios.delete(`/lke/clusters/${clusterId}/nodes/${nodeId}`);
    },
    recycleNode: async (clusterId: number, nodeId: string) => {
      await axios.post(`/lke/clusters/${clusterId}/nodes/${nodeId}/recycle`);
    },
    
    // Cluster access
    getKubeconfig: async (id: number) => {
      const response = await axios.get(`/lke/clusters/${id}/kubeconfig`);
      return response.data;
    },
    getAPIEndpoints: async (id: number) => {
      const response = await axios.get(`/lke/clusters/${id}/api-endpoints`);
      // Linode API returns endpoints as a paginated response, so extract the data array
      return response.data.data;
    },
    getDashboardURL: async (id: number) => {
      const response = await axios.get(`/lke/clusters/${id}/dashboard`);
      return response.data;
    },
    deleteServiceToken: async (id: number) => {
      await axios.delete(`/lke/clusters/${id}/servicetoken`);
    },
    
    // Version and type information
    getVersions: async () => {
      const response = await axios.get('/lke/versions');
      // Linode API returns versions as a paginated response, so extract the data array
      return response.data.data;
    },
    getVersion: async (version: string) => {
      const response = await axios.get(`/lke/versions/${version}`);
      return response.data;
    },
    getTypes: async () => {
      const response = await axios.get('/lke/types');
      // Linode API returns types as a paginated response, so extract the data array
      return response.data.data;
    }
  };
}