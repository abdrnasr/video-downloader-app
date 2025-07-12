import Image from "next/image";
import HomePageContent from "./components/homepagecontent";


export default function Home() {

  return (
    <>
      <div className={`w-screen h-screen flex flex-col overflow-y-auto overflow-x-hidden`}>
        <header className="h-16 shadow-[0px_1px_3px_-2px] shadow-shadowcast flex items-center justify-center bg-base-200">
          <Image className="" src="/main_logo.png" alt="Website Logo" width={50} height={50}/>
          <h1 className="ml-2 text-lg sm:text-2xl text-blue-600">Download Videos Online</h1>
        </header>

        <HomePageContent/>
      </div>
    </>
  );
}
