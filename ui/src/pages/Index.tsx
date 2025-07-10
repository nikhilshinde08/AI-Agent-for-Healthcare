import { MedicalHomepage } from '@/components/MedicalHomepage';
import { ChatButton } from '@/components/ChatButton';

const Index = () => {
  return (
    <>
      <MedicalHomepage />
      <ChatButton apiEndpoint="http://localhost:8002/chat" />
    </>
  );
};

export default Index;
