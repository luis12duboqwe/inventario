import Loader, { type LoaderVariant } from "../../shared/components/Loader";

export type LoaderProps = {
  message?: string;
  variant?: LoaderVariant;
  className?: string;
};

export { LoaderVariant };
export default Loader;
