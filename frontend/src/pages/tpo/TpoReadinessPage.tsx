import React from 'react';
import { DashboardLayout } from '../../components/layout/DashboardLayout';
import { TpoReadinessPanel } from '../../components/readiness/TpoReadinessPanel';

export const TpoReadinessPage: React.FC = () => {
  return (
    <DashboardLayout
      role="tpo"
      title="Institutional Placement Readiness Analytics"
      subtitle="Monitor cohort preparation across departments, batches, readiness bands, and skill categories — strictly advisory and separate from official eligibility."
    >
      <TpoReadinessPanel />
    </DashboardLayout>
  );
};

