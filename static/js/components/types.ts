export interface Collaborator {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  role: 'owner' | 'admin' | 'viewer';
}

export interface Issue {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'ui-ux' | 'security' | 'logic';
  screenshot?: string;
  step: number;
  timestamp: string;
  status: 'open' | 'in-progress' | 'resolved';
}
