const Footer = () => {
  return (
    <footer className="border-t bg-background h-14">
      <div className="container mx-auto px-4 h-full">
        <div className="grid grid-cols-3 gap-4 items-center h-full text-sm">
          <div>
            <h3 className="font-semibold">Ditto IoT Manager</h3>
            <p className="text-muted-foreground">
              Modern IoT device management platform
            </p>
          </div>

          <div className="text-right">
            <h3 className="font-semibold">Contact</h3>
            <div className="text-muted-foreground">support@dittoiot.com</div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
