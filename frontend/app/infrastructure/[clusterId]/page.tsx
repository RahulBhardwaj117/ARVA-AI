import { ClusterDetail } from "@/components/cluster-detail";

export default async function ClusterPage({
  params,
}: {
  params: Promise<{ clusterId: string }>;
}) {
  const { clusterId } = await params;
  return <ClusterDetail clusterId={clusterId} />;
}
