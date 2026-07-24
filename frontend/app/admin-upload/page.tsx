import { AdminUploadForm } from "@/components/admin-upload-form";
import { PageHeader } from "@/components/page-header";

export default async function AdminUploadPage() {
  return <div className="page"><PageHeader eyebrow="Protected workspace" title="Upload AASX" description="Authenticate with a Keycloak user account to add another Asset Administration Shell to the live workspace." /><AdminUploadForm /></div>;
}
